"""SyncWatermark — 동기화 진행 지점 영속 (이슈 05).

작은 Postgres 테이블 `public.sync_state`(key→value)에 마지막 처리 watermark
(예: 최대 it_update_time)를 저장해 워커 재시작 후에도 증분을 이어간다.
connect()의 search_path가 ag_catalog 우선이라 테이블을 public으로 명시한다.
"""
from __future__ import annotations

from apps.core.db import connect


class SyncWatermark:
    def __init__(self, connect_factory=connect):
        self._connect = connect_factory

    async def _ensure_table(self, cur) -> None:
        await cur.execute(
            "CREATE TABLE IF NOT EXISTS public.sync_state ("
            " key text PRIMARY KEY, value text NOT NULL)"
        )

    async def get(self, key: str, default: str | None = None) -> str | None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure_table(cur)
                await cur.execute("SELECT value FROM public.sync_state WHERE key = %s", (key,))
                row = await cur.fetchone()
        finally:
            await conn.close()
        return row[0] if row else default

    async def set(self, key: str, value: str) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure_table(cur)
                await cur.execute(
                    "INSERT INTO public.sync_state (key, value) VALUES (%s, %s) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                    (key, str(value)),
                )
        finally:
            await conn.close()
