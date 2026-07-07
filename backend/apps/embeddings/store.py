"""EmbeddingStore (이슈 01, ADR-0012) — Product 텍스트 임베딩 저장·최근접 검색.

ADR-0010으로 제거했던 임베딩을 실험(RESULTS.md) 근거로 재도입한다. pgvector에
(source_id, name, model, text_hash, embedding)로 저장하고, 같은 텍스트면 재임베딩을
스킵(캐시), 모델 버전을 태깅해 같은 모델끼리만 최근접 비교한다.
"""
from __future__ import annotations

import hashlib

from apps.core.db import connect
from apps.embeddings.filters import FILTER_COLUMNS, FILTER_SPEC


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


_KNOWN_FILTERS = {f.name for f in FILTER_SPEC}

# 검색 결과에 레지스트리 값(가격·순도·분자량·보관온도)을 함께 실어 리랭커가 숫자 판별을 하도록.
_SEARCH_COLS = "source_id, name" + "".join(f", {c}" for c in FILTER_COLUMNS)


def _hit(row) -> dict:
    """검색 행 → 후보 dict(레지스트리 값 포함, 없으면 None)."""
    return {
        "source_id": row[0], "name": row[1],
        **{c: row[2 + i] for i, c in enumerate(FILTER_COLUMNS)},
    }


def _filter_where(filters: dict | None) -> tuple[str, list]:
    """질의 필터 {name:(lo,hi)}(허용 범위) → 겹침 WHERE(ADR-0018).

    이하(hi): col_min<=hi · 이상(lo): col_max>=lo · 범위[lo,hi]: 둘 다. NULL 컬럼은 자동 제외.
    이름은 레지스트리로 검증(컬럼명 안전).
    """
    clauses: list[str] = []
    params: list = []
    for name, bounds in (filters or {}).items():
        if name not in _KNOWN_FILTERS:
            continue
        lo, hi = bounds
        if hi is not None:
            clauses.append(f"{name}_min <= %s")
            params.append(hi)
        if lo is not None:
            clauses.append(f"{name}_max >= %s")
            params.append(lo)
    where = ("".join(f" AND {c}" for c in clauses)) if clauses else ""
    return where, params


class FakeEmbeddingProvider:
    def __init__(self, model_version: str = "fake-embed-v1", dim: int = 8):
        self.model_version = model_version
        self._dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            out.append([h[i % len(h)] / 255.0 for i in range(self._dim)])
        return out


class OpenAIEmbeddingProvider:
    def __init__(self, model: str | None = None):
        import os

        self.model_version = model or os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import os

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.environ["OPEN_AI_KEY"])
        resp = await client.embeddings.create(model=self.model_version, input=texts)
        return [d.embedding for d in resp.data]


class EmbeddingStore:
    def __init__(self, provider, connect_factory=connect, table: str = "kg_embedding"):
        self._provider = provider
        self._connect = connect_factory
        assert table.replace("_", "").isalnum(), "table must be a safe identifier"
        self._table = f"public.{table}"

    async def _ensure(self, cur) -> None:
        await cur.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            " source_id text, name text, model text, text_hash text, content_hash text,"
            " embedding vector, PRIMARY KEY (source_id, model))"
        )
        # 기존 테이블에 content_hash가 없으면 추가(마이그레이션 — C: 적재 게이트 인덱스).
        await cur.execute(
            f"ALTER TABLE {self._table} ADD COLUMN IF NOT EXISTS content_hash text"
        )
        # 숫자 하드 필터 컬럼(ADR-0018) — 레지스트리 기준 min/max, 기존 행은 NULL.
        for col in FILTER_COLUMNS:
            await cur.execute(
                f"ALTER TABLE {self._table} ADD COLUMN IF NOT EXISTS {col} double precision"
            )

    async def reset(self) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"DROP TABLE IF EXISTS {self._table}")
                await self._ensure(cur)
        finally:
            await conn.close()

    async def ensure(self) -> None:
        """테이블·검색 인덱스를 1회 선생성한다(동시 백필 전 CREATE TABLE 레이스 방지)."""
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await self._ensure_search_index(cur)
        finally:
            await conn.close()

    async def _ensure_search_index(self, cur) -> None:
        """키워드 검색(name ILIKE) 고속화 — pg_trgm GIN 인덱스.

        권한이 없으면 조용히 건너뛴다(ILIKE는 인덱스 없이도 동작, 느릴 뿐).
        """
        try:
            await cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            idx = self._table.split(".")[-1] + "_name_trgm"
            await cur.execute(
                f"CREATE INDEX IF NOT EXISTS {idx} ON {self._table} "
                "USING gin (name gin_trgm_ops)"
            )
        except Exception:  # noqa: BLE001 — 인덱스는 성능 최적화일 뿐 필수 아님
            pass

    async def ensure_ann_index(self) -> bool:
        """대량 적재 후 1회 — HNSW 근사최근접 인덱스를 빌드한다(대규모 검색 가속).

        HNSW는 고정 차원 컬럼을 요구하므로, 저장된 임베딩에서 차원을 유도해(제공자 무관:
        fake=8·openai=1536) 컬럼을 vector(N)으로 한 번 고정한 뒤, 검색이 쓰는 L2
        연산자(`<->`)에 맞춰 vector_l2_ops HNSW를 만든다. 데이터가 없으면 차원을 알 수
        없어 False(안전 no-op), 만들었거나 이미 있으면 True. 권한이 없으면 조용히 False
        (인덱스는 성능 최적화일 뿐 — 인덱스가 없어도 전수 KNN으로 정확히 동작한다).

        소규모(수천)에선 플래너가 전수 스캔을 택해 이득이 없지만, 61만 규모에선 전수
        스캔(질의당 수백 ms)을 ~10ms로 낮춘다. 증분 삽입은 HNSW가 자동 유지한다.
        """
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT vector_dims(embedding) FROM {self._table} "
                    "WHERE embedding IS NOT NULL LIMIT 1"
                )
                row = await cur.fetchone()
                if not row:
                    return False  # 데이터 없음 → 차원 유도 불가 → HNSW 불가
                dim = int(row[0])
                try:
                    # 컬럼이 미고정(bare vector)일 때만 차원 고정 — 대형 테이블 반복 재작성 방지
                    await cur.execute(
                        "SELECT atttypmod FROM pg_attribute "
                        "WHERE attrelid = %s::regclass AND attname = 'embedding'",
                        (self._table,),
                    )
                    if (await cur.fetchone())[0] < 0:  # -1 = 차원 미지정
                        await cur.execute(
                            f"ALTER TABLE {self._table} "
                            f"ALTER COLUMN embedding TYPE vector({dim})"
                        )
                    idx = self._table.split(".")[-1] + "_hnsw"
                    await cur.execute(
                        f"CREATE INDEX IF NOT EXISTS {idx} ON {self._table} "
                        "USING hnsw (embedding vector_l2_ops)"
                    )
                except Exception:  # noqa: BLE001 — 인덱스는 성능 최적화일 뿐 필수 아님
                    return False
                return True
        finally:
            await conn.close()

    async def keyword_search(self, query: str, limit: int = 10, filters: dict | None = None) -> list[dict]:
        """상품명에 질의 토큰(OR·대소문자 무시)이 포함된 상품 — 시맨틱이 놓치는 정확어·코드 보완.

        토큰 OR 매칭: "유리 플라스크"가 "메스플라스크"(플라스크 포함)에도 걸리도록.
        filters(숫자 하드 필터)가 있으면 함께 건다(ADR-0018).
        """
        model = self._provider.model_version
        tokens = [t for t in (query or "").lower().split() if t]
        if not tokens:
            return []
        n = max(1, min(int(limit), 50))
        conds = " OR ".join(["name ILIKE %s"] * len(tokens))
        fwhere, fparams = _filter_where(filters)
        params = (model, *[f"%{t}%" for t in tokens], *fparams, n)
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT {_SEARCH_COLS} FROM {self._table} "
                    f"WHERE model=%s AND ({conds}){fwhere} LIMIT %s",
                    params,
                )
                rows = await cur.fetchall()
        finally:
            await conn.close()
        return [_hit(r) for r in rows]

    async def embed_product(
        self, source_id: str, name: str, text: str, content_hash: str | None = None,
        filters: dict | None = None,
    ) -> bool:
        """상품 텍스트를 임베딩·저장한다. 같은 텍스트로 이미 캐시돼 있으면 False(스킵).

        content_hash는 소스 문서의 지문 — 적재 게이트·재조정에 쓰인다(C: kg_embedding이
        '적재된 상품' 인덱스). filters는 숫자 하드 필터 값({이름:(min,max)}, ADR-0018). 텍스트가
        같아 재임베딩을 건너뛰어도 content_hash·필터 컬럼은 최신화한다(소스에서 변할 수 있음).
        """
        model = self._provider.model_version
        text_hash = hashlib.sha256(f"{model}:{text}".encode("utf-8")).hexdigest()
        fvals = {}
        for f in FILTER_SPEC:  # 레지스트리 순서로 _min·_max 값
            lo, hi = (filters or {}).get(f.name, (None, None))
            fvals[f"{f.name}_min"] = lo
            fvals[f"{f.name}_max"] = hi
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT text_hash FROM {self._table} WHERE source_id=%s AND model=%s",
                    (source_id, model),
                )
                row = await cur.fetchone()
                if row and row[0] == text_hash:  # 재임베딩 스킵 — content_hash·필터만 갱신
                    sets = ["content_hash=%s"] + [f"{c}=%s" for c in FILTER_COLUMNS]
                    params = [content_hash] + [fvals[c] for c in FILTER_COLUMNS] + [source_id, model]
                    await cur.execute(
                        f"UPDATE {self._table} SET {', '.join(sets)} "
                        "WHERE source_id=%s AND model=%s", params,
                    )
                    return False
                [vec] = await self._provider.embed([text])
                fcols_sql = "".join(f", {c}" for c in FILTER_COLUMNS)
                fplace = "".join(", %s" for _ in FILTER_COLUMNS)
                fset = "".join(f", {c}=EXCLUDED.{c}" for c in FILTER_COLUMNS)
                await cur.execute(
                    f"INSERT INTO {self._table} "
                    f"(source_id, name, model, text_hash, content_hash, embedding{fcols_sql}) "
                    f"VALUES (%s,%s,%s,%s,%s,%s::vector{fplace}) "
                    "ON CONFLICT (source_id, model) DO UPDATE SET name=EXCLUDED.name, "
                    f"text_hash=EXCLUDED.text_hash, content_hash=EXCLUDED.content_hash, "
                    f"embedding=EXCLUDED.embedding{fset}",
                    (source_id, name, model, text_hash, content_hash, _vec_literal(vec),
                     *[fvals[c] for c in FILTER_COLUMNS]),
                )
        finally:
            await conn.close()
        return True

    async def get_content_hash(self, source_id: str) -> str | None:
        """적재 게이트용 — 저장된 소스 문서 지문(없으면 None)."""
        model = self._provider.model_version
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT content_hash FROM {self._table} WHERE source_id=%s AND model=%s",
                    (source_id, model),
                )
                row = await cur.fetchone()
        finally:
            await conn.close()
        return row[0] if row else None

    async def content_hashes(self) -> dict[str, str]:
        """재조정용 — 적재된 모든 상품의 source_id → content_hash 스냅샷."""
        model = self._provider.model_version
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT source_id, content_hash FROM {self._table} WHERE model=%s",
                    (model,),
                )
                rows = await cur.fetchall()
        finally:
            await conn.close()
        return {r[0]: (r[1] or "") for r in rows}

    async def delete(self, source_id: str) -> None:
        """상품 임베딩을 제거한다(소스에서 사라진 상품 — 모든 모델 버전)."""
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"DELETE FROM {self._table} WHERE source_id=%s", (source_id,)
                )
        finally:
            await conn.close()

    async def ensure_indexes(self) -> None:
        """대규모 적재 전 테이블·검색 인덱스 선생성(ensure의 별칭)."""
        await self.ensure()

    async def search(self, query: str, k: int = 10, filters: dict | None = None) -> list[dict]:
        model = self._provider.model_version
        [qv] = await self._provider.embed([query])
        fwhere, fparams = _filter_where(filters)  # 숫자 하드 필터 + 시맨틱 동시(ADR-0018)
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT {_SEARCH_COLS} FROM {self._table} WHERE model=%s{fwhere} "
                    "ORDER BY embedding <-> %s::vector LIMIT %s",
                    (model, *fparams, _vec_literal(qv), k),
                )
                rows = await cur.fetchall()
        finally:
            await conn.close()
        return [_hit(r) for r in rows]


class SemanticSearch:
    """Recommendation Agent의 semantic_search 도구 — 운영 임베딩 저장소 위 의미 검색."""

    def __init__(self, provider=None, table: str = "kg_embedding"):
        self._store = EmbeddingStore(provider or OpenAIEmbeddingProvider(), table=table)

    async def search(self, keyword: str, k: int = 10, filters: dict | None = None) -> list[dict]:
        return await self._store.search(keyword, k=k, filters=filters)
