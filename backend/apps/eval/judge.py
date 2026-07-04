"""Judge (이슈 06) — 블라인드 쌍별·순서스왑 심사 + 집계.

두 config의 답을 정체 숨김(블라인드)으로 비교하고, A/B 순서를 양방향으로 판정해
위치편향을 상쇄한다. 판정은 캐시한다. 집계는 순수 함수(결정적).
"""
from __future__ import annotations

import json

from apps.core.db import connect


def combine(winner_ab: str, winner_ba: str) -> str:
    """순서스왑 두 판정을 합친다. 양방향 일치(비무승부)면 승자, 아니면 tie(위치편향)."""
    return winner_ab if (winner_ab == winner_ba and winner_ab != "tie") else "tie"


def aggregate(records: list[dict]) -> dict:
    """records: {stratum, config_a, config_b, winner} → config별 승률(전체/계층별)."""
    overall: dict[str, dict] = {}
    by_stratum: dict[str, dict] = {}

    def bump(table: dict, cfg: str, won: bool) -> None:
        entry = table.setdefault(cfg, {"wins": 0, "comparisons": 0})
        entry["comparisons"] += 1
        if won:
            entry["wins"] += 1

    for r in records:
        ca, cb, winner, stratum = r["config_a"], r["config_b"], r["winner"], r["stratum"]
        st = by_stratum.setdefault(stratum, {})
        for cfg in (ca, cb):
            bump(overall, cfg, winner == cfg)
            bump(st, cfg, winner == cfg)

    def finalize(table: dict) -> None:
        for entry in table.values():
            c = entry["comparisons"]
            entry["win_rate"] = round(entry["wins"] / c, 3) if c else 0.0

    finalize(overall)
    for st in by_stratum.values():
        finalize(st)
    return {"overall": overall, "by_stratum": by_stratum}


class Judge:
    def __init__(self, judge_fn, connect_factory=connect, model: str = "gpt-4o", table: str = "eval_judge"):
        # judge_fn(query_text, first_answer, second_answer) -> "1" | "2" | "tie"  (블라인드, 위치 기반)
        self._judge_fn = judge_fn
        self._connect = connect_factory
        self._model = model
        assert table.replace("_", "").isalnum(), "table must be a safe identifier"
        self._table = f"public.{table}"

    async def _ensure(self, cur) -> None:
        await cur.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            " query_id text, config_a text, config_b text, ord text, model text, winner text,"
            " PRIMARY KEY (query_id, config_a, config_b, ord, model))"
        )

    async def reset(self) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"DROP TABLE IF EXISTS {self._table}")
                await self._ensure(cur)
        finally:
            await conn.close()

    async def _get(self, query_id, ca, cb, order) -> str | None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"SELECT winner FROM {self._table} "
                    "WHERE query_id=%s AND config_a=%s AND config_b=%s AND ord=%s AND model=%s",
                    (query_id, ca, cb, order, self._model),
                )
                row = await cur.fetchone()
        finally:
            await conn.close()
        return row[0] if row else None

    async def _put(self, query_id, ca, cb, order, winner) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(
                    f"INSERT INTO {self._table} (query_id, config_a, config_b, ord, model, winner) "
                    "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (query_id, ca, cb, order, self._model, winner),
                )
        finally:
            await conn.close()

    async def verdict(self, query_id, query_text, ca, ans_a, cb, ans_b, order) -> str:
        """order('ab'|'ba')에 따라 답을 배치·판정하고, 위치를 config로 되매핑한다(캐시)."""
        cached = await self._get(query_id, ca, cb, order)
        if cached is not None:
            return cached
        first, second = (ans_a, ans_b) if order == "ab" else (ans_b, ans_a)
        pos = await self._judge_fn(query_text, first, second)
        if pos == "tie":
            winner = "tie"
        elif order == "ab":
            winner = ca if pos == "1" else cb
        else:
            winner = cb if pos == "1" else ca
        await self._put(query_id, ca, cb, order, winner)
        return winner
