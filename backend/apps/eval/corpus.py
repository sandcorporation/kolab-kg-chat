"""EvalCorpus (이슈 00) — 실 카탈로그에서 계층 태그를 붙여 평가 코퍼스를 선별·영속.

차이를 드러낼 케이스를 의도적으로 태깅한다: mixed_script(한/영 미스매치 후보),
image_only(스펙이 이미지에만), structured_rich(field_info 보유). 선별은 시드 고정 시
재현 가능(결정적). 후보는 주입 가능해 로직을 소규모로 테스트한다.
"""
from __future__ import annotations

import hashlib
import json

from apps.core.db import connect

_IMAGE_ONLY_EXPLAN_MAX = 80  # 이보다 설명이 짧고 field_info 없으면 스펙이 이미지에만 있을 가능성
# 희소·중요 계층부터 최소 커버를 보장한다(비교 판별력을 위해).
STRATA = ("image_only", "mixed_script", "structured_rich")


def _has_hangul(s: str) -> bool:
    return any("가" <= ch <= "힣" for ch in s)


def _has_ascii_letter(s: str) -> bool:
    return any(ch.isascii() and ch.isalpha() for ch in s)


def tag_candidate(c: dict) -> list[str]:
    tags: list[str] = []
    name = c.get("name") or ""
    if _has_hangul(name) and _has_ascii_letter(name):
        tags.append("mixed_script")
    if c.get("has_field_info"):
        tags.append("structured_rich")
    if c.get("has_image") and not c.get("has_field_info") and (c.get("explan_len") or 0) < _IMAGE_ONLY_EXPLAN_MAX:
        tags.append("image_only")
    return tags


class EvalCorpus:
    def __init__(self, connect_factory=connect, table: str = "eval_corpus"):
        self._connect = connect_factory
        assert table.replace("_", "").isalnum(), "table must be a safe identifier"
        self._table = f"public.{table}"

    async def _ensure(self, cur) -> None:
        await cur.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            " source_id text PRIMARY KEY, tags jsonb NOT NULL)"
        )

    async def reset(self) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"DROP TABLE IF EXISTS {self._table}")
                await self._ensure(cur)
        finally:
            await conn.close()

    @staticmethod
    def _order_key(seed: int, source_id: str) -> str:
        return hashlib.sha256(f"{seed}:{source_id}".encode()).hexdigest()

    async def build(self, candidates, target: int = 250, seed: int = 0) -> int:
        tagged = [(c["source_id"], tag_candidate(c)) for c in candidates]
        tagged.sort(key=lambda t: self._order_key(seed, t[0]))  # 결정적 셔플

        picked: list[tuple[str, list[str]]] = []
        chosen: set[str] = set()
        # 1) 각 계층 최소 1개(존재하는 계층만) — 희소 계층 커버 보장
        for stratum in STRATA:
            if len(picked) >= target:
                break
            for source_id, tags in tagged:
                if stratum in tags and source_id not in chosen:
                    picked.append((source_id, tags))
                    chosen.add(source_id)
                    break
        # 2) 나머지 슬롯을 결정적 순서로 채움
        for source_id, tags in tagged:
            if len(picked) >= target:
                break
            if source_id not in chosen:
                picked.append((source_id, tags))
                chosen.add(source_id)

        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                for source_id, tags in picked:
                    await cur.execute(
                        f"INSERT INTO {self._table} (source_id, tags) VALUES (%s, %s) "
                        "ON CONFLICT (source_id) DO UPDATE SET tags = EXCLUDED.tags",
                        (source_id, json.dumps(tags)),
                    )
        finally:
            await conn.close()
        return len(picked)

    async def list(self) -> list[dict]:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(f"SELECT source_id, tags FROM {self._table} ORDER BY source_id")
                rows = await cur.fetchall()
        finally:
            await conn.close()
        return [{"source_id": r[0], "tags": r[1]} for r in rows]
