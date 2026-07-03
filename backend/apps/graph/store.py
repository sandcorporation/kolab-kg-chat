"""GraphStore — Postgres+AGE 위의 Knowledge Graph 딥모듈 (이슈 06, ADR-0003·0008).

Product/Variant 노드와 HAS_VARIANT 엣지를 소스 PK 기준으로 멱등 upsert한다.
cypher 호출은 AGE를, 파라미터는 agtype(JSON)으로 전달한다.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

from apps.core.db import connect

# NOTE: AGE는 짧은 이름 "kg"를 create_graph에서 거부한다("graph name is invalid").
GRAPH_NAME = "knowledge_graph"


class GraphStore:
    def __init__(self, connect_factory=connect, graph_name: str = GRAPH_NAME):
        self._connect = connect_factory
        self._graph = graph_name
        self._session_conn = None  # batch() 내에서 재사용하는 공용 커넥션

    # ── 커넥션 수명 (배치 세션이면 재사용, 아니면 단건) ──
    async def _acquire(self):
        if self._session_conn is not None:
            return self._session_conn
        return await self._connect()

    async def _release(self, conn) -> None:
        if conn is not self._session_conn:
            await conn.close()

    @asynccontextmanager
    async def batch(self):
        """배치 동안 커넥션 1개(+LOAD age 1회)를 재사용하고 끝에 커밋한다(이슈 03).

        대량 적재에서 상품마다 커넥션을 새로 여는 비용·LOAD age를 제거한다.
        """
        conn = await self._connect(autocommit=False)
        try:
            async with conn.cursor() as cur:
                await cur.execute("SET LOCAL synchronous_commit = off")  # 대량 적재 속도
            self._session_conn = conn
            yield self
            await conn.commit()
        except BaseException:
            await conn.rollback()
            raise
        finally:
            self._session_conn = None
            await conn.close()

    # ── 내부 cypher 실행 ──
    async def _cypher(self, cur, query: str, params: dict | None = None, columns: str = "(a agtype)"):
        if params is None:
            await cur.execute(f"SELECT * FROM cypher('{self._graph}', $$ {query} $$) AS {columns}")
        else:
            await cur.execute(
                f"SELECT * FROM cypher('{self._graph}', $$ {query} $$, %s::agtype) AS {columns}",
                (json.dumps(params),),
            )
        return await cur.fetchall()

    async def _ensure_graph(self, cur) -> None:
        await cur.execute(
            "SELECT count(*) FROM ag_catalog.ag_graph WHERE name = %s", (self._graph,)
        )
        (n,) = await cur.fetchone()
        if n == 0:
            await cur.execute("SELECT create_graph(%s)", (self._graph,))

    # AGE는 속성 조회를 자동 인덱싱하지 않는다 → 대규모에서 MATCH {source_id}가 전체 스캔.
    # 아래 btree 인덱스로 적재/조회를 O(N²)에서 벗어나게 한다(이슈 01).
    _INDEX_SPECS = (
        ("Product", "source_id"),
        ("Variant", "variant_key"),
        ("Attribute", "name"),
        ("Attribute", "value"),
    )

    async def _ensure_vlabel(self, cur, label: str) -> None:
        await cur.execute(
            "SELECT count(*) FROM ag_catalog.ag_label l "
            "JOIN ag_catalog.ag_graph g ON l.graph = g.graphid "
            "WHERE g.name = %s AND l.name = %s",
            (self._graph, label),
        )
        (n,) = await cur.fetchone()
        if n == 0:
            await cur.execute("SELECT create_vlabel(%s, %s)", (self._graph, label))

    async def ensure_indexes(self) -> None:
        """AGE 정점 속성에 btree 인덱스를 멱등 생성한다(이슈 01)."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                for label, prop in self._INDEX_SPECS:
                    await self._ensure_vlabel(cur, label)
                    idx = f"ix_{label.lower()}_{prop}"
                    # prop/label은 내부 상수 → 리터럴 인라인(파라미터는 DDL 표현식에서 타입 추론 불가)
                    await cur.execute(
                        f'CREATE INDEX IF NOT EXISTS {idx} ON {self._graph}."{label}" '
                        "USING btree (ag_catalog.agtype_access_operator("
                        f"VARIADIC ARRAY[properties, '\"{prop}\"'::agtype]))"
                    )
        finally:
            await self._release(conn)

    async def index_names(self) -> list[str]:
        """그래프 스키마에 존재하는 인덱스 이름 목록(점검·테스트용)."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = %s", (self._graph,)
                )
                rows = await cur.fetchall()
        finally:
            await self._release(conn)
        return [r[0] for r in rows]

    # ── 테스트/운영 보조 ──
    async def reset(self) -> None:
        """그래프를 비우고 새로 만든다(테스트 격리용)."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT count(*) FROM ag_catalog.ag_graph WHERE name = %s", (self._graph,)
                )
                (n,) = await cur.fetchone()
                if n:
                    await cur.execute("SELECT drop_graph(%s, true)", (self._graph,))
                await cur.execute("SELECT create_graph(%s)", (self._graph,))
        finally:
            await self._release(conn)

    # ── 쓰기 ──
    async def upsert_product(self, doc) -> None:
        """Product + Variant 를 소스 PK 기준으로 멱등 upsert한다."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                await self._cypher(
                    cur,
                    # description(it_explan HTML)은 읽기 경로 미사용 → 저장 안 함(대규모 절감, 이슈 02)
                    "MERGE (p:Product {source_id: $sid}) "
                    "SET p.name = $name, p.brand = $brand, p.category_path = $cat, "
                    "p.content_hash = $hash, p.image_url = $img "
                    "RETURN p",
                    {
                        "sid": doc.source_id,
                        "name": doc.name,
                        "brand": doc.brand,
                        "cat": list(doc.category_path),
                        "hash": doc.content_hash,
                        "img": doc.images[0].url if doc.images else "",
                    },
                    columns="(p agtype)",
                )
                # 변형 집합을 현재 상태로 재구성(삭제된 옵션 반영, 멱등)
                await self._cypher(
                    cur,
                    "MATCH (:Product {source_id: $sid})-[:HAS_VARIANT]->(v:Variant) DETACH DELETE v",
                    {"sid": doc.source_id},
                )
                for v in doc.variants:
                    await self._cypher(
                        cur,
                        "MATCH (p:Product {source_id: $sid}) "
                        "CREATE (p)-[:HAS_VARIANT]->(:Variant {variant_key: $vk, label: $label, price: $price})",
                        {
                            "sid": doc.source_id,
                            "vk": v.variant_key,
                            "label": v.label,
                            "price": v.price,
                        },
                    )
        finally:
            await self._release(conn)

    async def delete_product(self, source_id: str) -> None:
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                await self._cypher(
                    cur,
                    "MATCH (:Product {source_id: $sid})-[:HAS_VARIANT]->(v:Variant) DETACH DELETE v",
                    {"sid": source_id},
                )
                await self._cypher(
                    cur,
                    "MATCH (p:Product {source_id: $sid}) DETACH DELETE p",
                    {"sid": source_id},
                )
        finally:
            await self._release(conn)

    async def set_attributes(self, source_id: str, attributes: list[dict]) -> None:
        """Product의 Functional Attribute를 현재 추출 결과로 교체한다(멱등).

        attributes: {name, value, provenance, confidence, is_candidate} dict 목록.
        """
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                await self._cypher(
                    cur,
                    "MATCH (:Product {source_id: $sid})-[:HAS_ATTRIBUTE]->(a:Attribute) DETACH DELETE a",
                    {"sid": source_id},
                )
                for attr in attributes:
                    await self._cypher(
                        cur,
                        "MATCH (p:Product {source_id: $sid}) "
                        "CREATE (p)-[:HAS_ATTRIBUTE]->(:Attribute {name: $name, value: $value, "
                        "provenance: $prov, confidence: $conf, is_candidate: $cand})",
                        {
                            "sid": source_id,
                            "name": attr["name"],
                            "value": attr["value"],
                            "prov": attr["provenance"],
                            "conf": attr["confidence"],
                            "cand": attr["is_candidate"],
                        },
                    )
        finally:
            await self._release(conn)

    async def get_attributes(self, source_id: str) -> list[dict]:
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur,
                    "MATCH (:Product {source_id: $sid})-[:HAS_ATTRIBUTE]->(a:Attribute) "
                    "RETURN a.name, a.value, a.provenance, a.confidence, a.is_candidate",
                    {"sid": source_id},
                    columns="(name agtype, value agtype, provenance agtype, confidence agtype, is_candidate agtype)",
                )
        finally:
            await self._release(conn)
        return [
            {
                "name": json.loads(r[0]),
                "value": json.loads(r[1]),
                "provenance": json.loads(r[2]),
                "confidence": json.loads(r[3]),
                "is_candidate": json.loads(r[4]),
            }
            for r in rows
        ]

    async def set_variant_attributes(self, variant_key: str, attributes: list[dict]) -> None:
        """기능 변형의 Functional Attribute를 해당 Variant 노드에 부착한다(Matching Unit)."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                await self._cypher(
                    cur,
                    "MATCH (:Variant {variant_key: $vk})-[:HAS_ATTRIBUTE]->(a:Attribute) DETACH DELETE a",
                    {"vk": variant_key},
                )
                for attr in attributes:
                    await self._cypher(
                        cur,
                        "MATCH (v:Variant {variant_key: $vk}) "
                        "CREATE (v)-[:HAS_ATTRIBUTE]->(:Attribute {name: $name, value: $value, "
                        "provenance: $prov, confidence: $conf, is_candidate: $cand})",
                        {
                            "vk": variant_key,
                            "name": attr["name"],
                            "value": attr["value"],
                            "prov": attr["provenance"],
                            "conf": attr["confidence"],
                            "cand": attr["is_candidate"],
                        },
                    )
        finally:
            await self._release(conn)

    async def get_variant_attributes(self, variant_key: str) -> list[dict]:
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur,
                    "MATCH (:Variant {variant_key: $vk})-[:HAS_ATTRIBUTE]->(a:Attribute) "
                    "RETURN a.name, a.value",
                    {"vk": variant_key},
                    columns="(name agtype, value agtype)",
                )
        finally:
            await self._release(conn)
        return [{"name": json.loads(r[0]), "value": json.loads(r[1])} for r in rows]

    # ── 읽기 ──
    async def list_products(self) -> list[dict]:
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur,
                    "MATCH (p:Product) "
                    "OPTIONAL MATCH (p)-[:HAS_VARIANT]->(v:Variant) "
                    "RETURN p.source_id, p.name, p.brand, count(v)",
                    columns="(source_id agtype, name agtype, brand agtype, vcount agtype)",
                )
        finally:
            await self._release(conn)
        return [
            {
                "source_id": json.loads(r[0]),
                "name": json.loads(r[1]),
                "brand": json.loads(r[2]),
                "variant_count": json.loads(r[3]),
            }
            for r in rows
        ]

    async def content_hashes(self) -> dict[str, str]:
        """그래프의 현재 상태 스냅샷(source_id → content_hash). 폴링 delta의 기준선."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur,
                    "MATCH (p:Product) RETURN p.source_id, p.content_hash",
                    columns="(source_id agtype, content_hash agtype)",
                )
        finally:
            await self._release(conn)
        out: dict[str, str] = {}
        for r in rows:
            if r[1] is not None:
                out[json.loads(r[0])] = json.loads(r[1])
        return out

    async def get_content_hash(self, source_id: str) -> str | None:
        """저장된 Product의 content_hash(없으면 None) — delta 게이팅용(ADR-0008)."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur,
                    "MATCH (p:Product {source_id: $sid}) RETURN p.content_hash",
                    {"sid": source_id},
                    columns="(h agtype)",
                )
        finally:
            await self._release(conn)
        if not rows:
            return None
        return json.loads(rows[0][0])

    async def add_compatibility(self, a: str, b: str, kind: str = "compatible_with") -> None:
        """Product a -[:COMPATIBLE_WITH]-> b 엣지를 멱등 생성한다(이슈 18)."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                await self._cypher(
                    cur,
                    "MERGE (x:Product {source_id: $a}) "
                    "MERGE (y:Product {source_id: $b}) "
                    "MERGE (x)-[r:COMPATIBLE_WITH]->(y) SET r.kind = $kind",
                    {"a": a, "b": b, "kind": kind},
                )
        finally:
            await self._release(conn)

    async def find_compatible(self, source_id: str, max_depth: int = 3) -> list[dict]:
        """X에서 COMPATIBLE_WITH 엣지를 1..max_depth 홉 순회한 도달 Product(최소 깊이)."""
        depth = max(1, int(max_depth))
        query = (
            f"MATCH path = (a:Product {{source_id: $sid}})-[:COMPATIBLE_WITH*1..{depth}]->(c:Product) "
            "RETURN c.source_id, length(path)"
        )
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur, query, {"sid": source_id}, columns="(source_id agtype, depth agtype)"
                )
        finally:
            await self._release(conn)
        best: dict[str, int] = {}
        for r in rows:
            sid = json.loads(r[0])
            d = json.loads(r[1])
            if sid not in best or d < best[sid]:
                best[sid] = d
        return [{"source_id": s, "depth": d} for s, d in best.items()]

    async def search_products(self, keyword: str, limit: int = 10) -> list[dict]:
        """상품명에 keyword가 포함된 상품(대소문자 무시). 에이전트의 진입 검색 도구.

        자연어 질의를 이름에 매칭하는 유일한 경로 — 속성 필터(find_products) 전에 후보를 좁힌다.
        """
        tokens = [t for t in (keyword or "").lower().split() if t]
        if not tokens:
            return []
        n = max(1, min(int(limit), 50))
        # 구절이 아니라 토큰 OR 매칭 — "유리 플라스크"가 "메스플라스크"(플라스크 포함)에도 걸리도록.
        conds = " OR ".join(f"toLower(p.name) CONTAINS $t{i}" for i in range(len(tokens)))
        params = {f"t{i}": t for i, t in enumerate(tokens)}
        query = f"MATCH (p:Product) WHERE {conds} RETURN p.source_id, p.name LIMIT {n}"
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur, query, params, columns="(source_id agtype, name agtype)"
                )
        finally:
            await self._release(conn)
        return [{"source_id": json.loads(r[0]), "name": json.loads(r[1])} for r in rows]

    _OPS = {"==": "=", "<=": "<=", ">=": ">=", "<": "<", ">": ">"}

    async def find_products_by_conditions(self, conditions: list[dict]) -> list[str]:
        """모든 조건(AND)을 충족하는 Attribute를 가진 Product의 source_id 목록(이슈 16).

        각 조건: {name, op, value}. op은 ==,<=,>=,<,> 중 하나.
        """
        valid = [c for c in conditions if c.get("op") in self._OPS]
        if not valid:
            return []
        matches = " ".join(
            f"MATCH (p)-[:HAS_ATTRIBUTE]->(a{i}:Attribute)" for i in range(len(valid))
        )
        wheres = " AND ".join(
            f"a{i}.name = $n{i} AND a{i}.value {self._OPS[c['op']]} $v{i}"
            for i, c in enumerate(valid)
        )
        params: dict = {}
        for i, c in enumerate(valid):
            params[f"n{i}"] = c["name"]
            params[f"v{i}"] = c["value"]
        query = f"MATCH (p:Product) {matches} WHERE {wheres} RETURN DISTINCT p.source_id"

        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(cur, query, params, columns="(source_id agtype)")
        finally:
            await self._release(conn)
        return [json.loads(r[0]) for r in rows]

    async def price_range(self, source_id: str) -> tuple[int | None, int | None]:
        """상품 변형 가격의 최저·최고(가격 없는 변형 제외). 하나도 없으면 (None, None)."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur,
                    "MATCH (p:Product {source_id: $sid})-[:HAS_VARIANT]->(v:Variant) "
                    "WHERE v.price IS NOT NULL "
                    "RETURN min(v.price), max(v.price)",
                    {"sid": source_id},
                    columns="(lo agtype, hi agtype)",
                )
        finally:
            await self._release(conn)
        if not rows or rows[0][0] is None:
            return (None, None)
        lo, hi = rows[0]
        return (int(json.loads(lo)), int(json.loads(hi)))

    async def get_product(self, source_id: str) -> dict | None:
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await self._ensure_graph(cur)
                rows = await self._cypher(
                    cur,
                    "MATCH (p:Product {source_id: $sid}) "
                    "OPTIONAL MATCH (p)-[:HAS_VARIANT]->(v:Variant) "
                    "RETURN p.name, p.brand, count(v), p.image_url",
                    {"sid": source_id},
                    columns="(name agtype, brand agtype, vcount agtype, image_url agtype)",
                )
        finally:
            await self._release(conn)
        if not rows:
            return None
        r = rows[0]
        return {
            "name": json.loads(r[0]),
            "brand": json.loads(r[1]),
            "variant_count": json.loads(r[2]),
            "image_url": json.loads(r[3]) if r[3] is not None else None,
        }
