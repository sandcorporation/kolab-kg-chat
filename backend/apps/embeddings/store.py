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
            " source_id text, name text, model text, text_hash text, embedding vector,"
            " PRIMARY KEY (source_id, model))"
        )

    async def reset(self) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"DROP TABLE IF EXISTS {self._table}")
                await self._ensure(cur)
        finally:
            await conn.close()

    async def embed_product(self, source_id: str, name: str, text: str) -> bool:
        """상품 텍스트를 임베딩·저장한다. 같은 텍스트로 이미 캐시돼 있으면 False(스킵)."""
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
                    return False
                [vec] = await self._provider.embed([text])
                await cur.execute(
                    f"INSERT INTO {self._table} (source_id, name, model, text_hash, embedding) "
                    "VALUES (%s,%s,%s,%s,%s::vector) "
                    "ON CONFLICT (source_id, model) DO UPDATE SET name=EXCLUDED.name, "
                    "text_hash=EXCLUDED.text_hash, embedding=EXCLUDED.embedding",
                    (source_id, name, model, text_hash, _vec_literal(vec)),
                )
        finally:
            await conn.close()
        return True

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
