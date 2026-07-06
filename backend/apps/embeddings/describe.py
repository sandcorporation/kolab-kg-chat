"""ProductDescriber (이슈 01, Route C) — 적재 시 상품 임베딩을 풍부화하는 설명 생성.

카탈로그 상품명이 영어라 한국어 질의가 검색을 놓치는 KO/EN 미스매치를, 상품마다 LLM이
한/영 설명·키워드를 생성해 임베딩 텍스트에 넣어 메운다(embed-chat GraphRAG 원리 이식).
설명 생성은 content-hash로 게이팅·캐시한다 — 안 바뀐 상품은 재호출하지 않는다.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from apps.core.db import connect

DESCRIBE_PROMPT = (
    "이 실험·연구 장비 상품의 유형과 용도를 한국어와 영어로 각각 한 줄로 설명하고, "
    "검색에 쓸 한/영 키워드를 나열하라. 3줄 이내, 군더더기 없이."
)


class DescriptionStore:
    """상품 설명 캐시 — source_id → (content_hash, description)."""

    def __init__(self, connect_factory=connect, table: str = "kg_description"):
        self._connect = connect_factory
        assert table.replace("_", "").isalnum(), "table must be a safe identifier"
        self._table = f"public.{table}"

    async def _ensure(self, cur) -> None:
        await cur.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            " source_id text PRIMARY KEY, content_hash text, description text)"
        )

    async def reset(self) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"DROP TABLE IF EXISTS {self._table}")
                await self._ensure(cur)
        finally:
            await conn.close()

    async def get(self, source_id: str) -> tuple[str | None, str | None]:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT content_hash, description FROM {self._table} WHERE source_id=%s",
                    (source_id,),
                )
                row = await cur.fetchone()
        finally:
            await conn.close()
        return (row[0], row[1]) if row else (None, None)

    async def put(self, source_id: str, content_hash: str, description: str) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"INSERT INTO {self._table} (source_id, content_hash, description) "
                    "VALUES (%s,%s,%s) ON CONFLICT (source_id) DO UPDATE SET "
                    "content_hash=EXCLUDED.content_hash, description=EXCLUDED.description",
                    (source_id, content_hash, description),
                )
        finally:
            await conn.close()


class ProductDescriber:
    def __init__(self, model, store: DescriptionStore):
        self._model = model
        self._store = store

    async def describe(self, source_id: str, name: str, attributes: list[dict], content_hash: str) -> str:
        cached_hash, cached = await self._store.get(source_id)
        if cached_hash == content_hash and cached is not None:
            return cached                            # content-hash 게이팅: 재호출 없음
        try:
            resp = await self._model.ainvoke([
                SystemMessage(content=DESCRIBE_PROMPT),
                HumanMessage(content=f"상품명: {name}\n속성: {_fmt(attributes)}"),
            ])
            desc = getattr(resp, "content", "") or ""
        except Exception:  # noqa: BLE001 — 설명 생성 실패는 적재를 막지 않는다(폴백)
            return ""
        await self._store.put(source_id, content_hash, desc)
        return desc


def _fmt(attributes: list[dict]) -> str:
    return ", ".join(f"{a['name']}={a['value']}" for a in attributes) or "속성 없음"
