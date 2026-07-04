"""EvalRunner (이슈 01) — config×query 에이전트 답변을 캐시한다.

(config_id, query_id, agent_version) 키로 답변(rationale + 추천 카드)을 영속해,
재실행 시 에이전트(LLM)를 다시 호출하지 않는다. 버전 키로 무효화한다.
"""
from __future__ import annotations

import json

from apps.core.db import connect


class EvalRunner:
    def __init__(self, connect_factory=connect, agent_version: str = "v1", table: str = "eval_run"):
        self._connect = connect_factory
        self._version = agent_version
        assert table.replace("_", "").isalnum(), "table must be a safe identifier"
        self._table = f"public.{table}"

    async def _ensure(self, cur) -> None:
        await cur.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            " config_id text, query_id text, agent_version text, answer jsonb NOT NULL,"
            " PRIMARY KEY (config_id, query_id, agent_version))"
        )

    async def reset(self) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"DROP TABLE IF EXISTS {self._table}")
                await self._ensure(cur)
        finally:
            await conn.close()

    async def _get(self, config_id: str, query_id: str) -> dict | None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT answer FROM {self._table} "
                    "WHERE config_id=%s AND query_id=%s AND agent_version=%s",
                    (config_id, query_id, self._version),
                )
                row = await cur.fetchone()
        finally:
            await conn.close()
        return row[0] if row else None

    async def _put(self, config_id: str, query_id: str, answer: dict) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"INSERT INTO {self._table} (config_id, query_id, agent_version, answer) "
                    "VALUES (%s,%s,%s,%s) ON CONFLICT (config_id, query_id, agent_version) "
                    "DO UPDATE SET answer = EXCLUDED.answer",
                    (config_id, query_id, self._version, json.dumps(answer, ensure_ascii=False)),
                )
        finally:
            await conn.close()

    async def store_answer(self, config_id: str, query_id: str, answer: dict) -> None:
        """실패 시 폴백 답을 캐시한다(재실행 스킵용)."""
        await self._put(config_id, query_id, answer)

    async def run(self, config_id: str, query_id: str, query_text: str, agent, enricher) -> dict:
        cached = await self._get(config_id, query_id)
        if cached is not None:
            return cached
        result = await agent.run(query_text)
        cards = await enricher.enrich(result.recommended_ids)
        answer = {"rationale": result.rationale, "products": cards}
        await self._put(config_id, query_id, answer)
        return answer
