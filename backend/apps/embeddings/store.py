"""EmbeddingStore (이슈 01, ADR-0012) — Product 텍스트 임베딩 저장·최근접 검색.

ADR-0010으로 제거했던 임베딩을 실험(RESULTS.md) 근거로 재도입한다. pgvector에
(source_id, name, model, text_hash, embedding)로 저장하고, 같은 텍스트면 재임베딩을
스킵(캐시), 모델 버전을 태깅해 같은 모델끼리만 최근접 비교한다.
"""
from __future__ import annotations

import hashlib

from apps.core.db import connect


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


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

    async def keyword_search(self, query: str, limit: int = 10) -> list[dict]:
        """상품명에 질의 토큰(OR·대소문자 무시)이 포함된 상품 — 시맨틱이 놓치는 정확어·코드 보완.

        토큰 OR 매칭: "유리 플라스크"가 "메스플라스크"(플라스크 포함)에도 걸리도록.
        """
        model = self._provider.model_version
        tokens = [t for t in (query or "").lower().split() if t]
        if not tokens:
            return []
        n = max(1, min(int(limit), 50))
        conds = " OR ".join(["name ILIKE %s"] * len(tokens))
        params = (model, *[f"%{t}%" for t in tokens], n)
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT source_id, name FROM {self._table} "
                    f"WHERE model=%s AND ({conds}) LIMIT %s",
                    params,
                )
                rows = await cur.fetchall()
        finally:
            await conn.close()
        return [{"source_id": r[0], "name": r[1]} for r in rows]

    async def embed_product(
        self, source_id: str, name: str, text: str, content_hash: str | None = None
    ) -> bool:
        """상품 텍스트를 임베딩·저장한다. 같은 텍스트로 이미 캐시돼 있으면 False(스킵).

        content_hash는 소스 문서의 지문 — 적재 게이트·재조정에 쓰인다(C: kg_embedding이
        '적재된 상품' 인덱스). 텍스트가 같아 재임베딩을 건너뛰어도 content_hash는 최신화한다.
        """
        model = self._provider.model_version
        text_hash = hashlib.sha256(f"{model}:{text}".encode("utf-8")).hexdigest()
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT text_hash FROM {self._table} WHERE source_id=%s AND model=%s",
                    (source_id, model),
                )
                row = await cur.fetchone()
                if row and row[0] == text_hash:
                    if content_hash is not None:
                        await cur.execute(
                            f"UPDATE {self._table} SET content_hash=%s "
                            "WHERE source_id=%s AND model=%s",
                            (content_hash, source_id, model),
                        )
                    return False
                [vec] = await self._provider.embed([text])
                await cur.execute(
                    f"INSERT INTO {self._table} "
                    "(source_id, name, model, text_hash, content_hash, embedding) "
                    "VALUES (%s,%s,%s,%s,%s,%s::vector) "
                    "ON CONFLICT (source_id, model) DO UPDATE SET name=EXCLUDED.name, "
                    "text_hash=EXCLUDED.text_hash, content_hash=EXCLUDED.content_hash, "
                    "embedding=EXCLUDED.embedding",
                    (source_id, name, model, text_hash, content_hash, _vec_literal(vec)),
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

    async def search(self, query: str, k: int = 10) -> list[dict]:
        model = self._provider.model_version
        [qv] = await self._provider.embed([query])
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT source_id, name FROM {self._table} WHERE model=%s "
                    "ORDER BY embedding <-> %s::vector LIMIT %s",
                    (model, _vec_literal(qv), k),
                )
                rows = await cur.fetchall()
        finally:
            await conn.close()
        return [{"source_id": r[0], "name": r[1]} for r in rows]


class SemanticSearch:
    """Recommendation Agent의 semantic_search 도구 — 운영 임베딩 저장소 위 의미 검색."""

    def __init__(self, provider=None, table: str = "kg_embedding"):
        self._store = EmbeddingStore(provider or OpenAIEmbeddingProvider(), table=table)

    async def search(self, keyword: str, k: int = 10) -> list[dict]:
        return await self._store.search(keyword, k=k)
