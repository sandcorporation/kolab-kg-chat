"""lean 임베딩 + semantic_search (이슈 04) — config 4 실험용.

ADR-0010으로 운영에선 임베딩을 제거했다. 이 모듈은 그 결정을 ablation으로 검증하려는
실험 전용이다(pgvector는 db 이미지에 남아 있음). Product당 name+속성 텍스트를 임베딩해
의미 유사도 top-k를 반환한다. 임베딩은 (source_id, model, text_hash)로 캐시한다.
"""
from __future__ import annotations

import hashlib

from apps.core.db import connect


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


class FakeEmbeddingProvider:
    model_version = "fake-embed-v1"

    def __init__(self, dim: int = 8):
        self._dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            out.append([h[i % len(h)] / 255.0 for i in range(self._dim)])
        return out


class OpenAIEmbeddingProvider:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model_version = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import os

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.environ["OPEN_AI_KEY"])
        resp = await client.embeddings.create(model=self.model_version, input=texts)
        return [d.embedding for d in resp.data]


class EvalEmbeddings:
    def __init__(self, provider, connect_factory=connect, table: str = "eval_embedding"):
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
        """상품 텍스트를 임베딩해 저장한다. 이미 같은 텍스트로 캐시돼 있으면 False(스킵)."""
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
    """config 4의 semantic_search 도구. 실 임베딩(text-embedding-3-small) 사용."""

    def __init__(self, graph_name: str = "eval_graph", provider=None, table: str = "eval_embedding"):
        self._emb = EvalEmbeddings(provider or OpenAIEmbeddingProvider(), table=table)

    async def search(self, keyword: str, k: int = 10) -> list[dict]:
        return await self._emb.search(keyword, k=k)
