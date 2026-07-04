"""절대 루브릭 점수 (config5 실험) — 답을 질의에 대해 0~3점으로 채점, 캐시.

쌍별 승률은 상대적이라 "다 낮다"가 안 보인다. 절대 점수로 천장을 드러내고,
config5가 그 천장을 넘는지 확인한다.
"""
from __future__ import annotations

import json
import os

from apps.core.db import connect


def aggregate_scores(records: list[dict]) -> dict:
    """records: {config_id, stratum, score} → config별 평균(전체/계층별)."""
    def means(pairs: dict) -> dict:
        return {cfg: round(sum(v) / len(v), 3) for cfg, v in pairs.items() if v}

    overall: dict[str, list] = {}
    by_stratum: dict[str, dict] = {}
    for r in records:
        overall.setdefault(r["config_id"], []).append(r["score"])
        by_stratum.setdefault(r["stratum"], {}).setdefault(r["config_id"], []).append(r["score"])
    return {
        "overall": means(overall),
        "by_stratum": {st: means(p) for st, p in by_stratum.items()},
    }


class Scorer:
    def __init__(self, score_fn, connect_factory=connect, model: str = "gpt-4o",
                 agent_version: str = "v1", table: str = "eval_score"):
        self._score_fn = score_fn
        self._connect = connect_factory
        self._model = model
        self._version = agent_version
        assert table.replace("_", "").isalnum(), "table must be a safe identifier"
        self._table = f"public.{table}"

    async def _ensure(self, cur) -> None:
        await cur.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            " config_id text, query_id text, agent_version text, model text, score int,"
            " PRIMARY KEY (config_id, query_id, agent_version, model))"
        )

    async def reset(self) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"DROP TABLE IF EXISTS {self._table}")
                await self._ensure(cur)
        finally:
            await conn.close()

    async def score(self, config_id: str, query_id: str, query_text: str, answer: dict) -> int:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT score FROM {self._table} "
                    "WHERE config_id=%s AND query_id=%s AND agent_version=%s AND model=%s",
                    (config_id, query_id, self._version, self._model),
                )
                row = await cur.fetchone()
                if row is not None:
                    return row[0]
        finally:
            await conn.close()

        value = int(await self._score_fn(query_text, answer))
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"INSERT INTO {self._table} (config_id, query_id, agent_version, model, score) "
                    "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (config_id, query_id, self._version, self._model, value),
                )
        finally:
            await conn.close()
        return value


def make_openai_score_fn(model: str):
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPEN_AI_KEY"])

    async def score_fn(query_text, answer):
        products = "\n".join(
            f"- {p.get('name', '')}" for p in (answer or {}).get("products", [])[:6]
        ) or "(추천 없음)"
        prompt = (
            f'질의: "{query_text}"\n추천 상품:\n{products}\n근거: {(answer or {}).get("rationale","")[:300]}\n\n'
            "이 추천이 질의에 얼마나 적합한지 0~3으로 채점하라. "
            "0=무관/빈손, 1=약간 관련, 2=대체로 적합, 3=매우 적합. "
            'JSON {"score":0|1|2|3} 만 출력.'
        )
        resp = await client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, temperature=0,
        )
        try:
            return int(json.loads(resp.choices[0].message.content).get("score", 0))
        except Exception:  # noqa: BLE001
            return 0

    return score_fn
