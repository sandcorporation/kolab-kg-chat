"""DiffPoller — 변경 감지 mock 폴러 (이슈 14, ADR-0002 폴링 fallback).

소스의 현재 상태 스냅샷(source_id → content_hash)을 이전 스냅샷과 비교해
created/updated/deleted 변경을 낸다. 실제 CDC(이슈 26)로 교체되는 자리이며,
binlog/WAL 접근이 불가할 때의 reconciliation 폴링 fallback이기도 하다.
"""
from __future__ import annotations

from apps.connectors.base import ProductChanged


class DiffPoller:
    def __init__(self, connector):
        self._connector = connector

    async def snapshot(self) -> dict[str, str]:
        snap: dict[str, str] = {}
        async for source_id in self._connector.iter_product_ids():
            doc = await self._connector.assemble(source_id)
            if doc is not None:
                snap[source_id] = doc.content_hash
        return snap

    async def poll(self, previous: dict[str, str]) -> tuple[list[ProductChanged], dict[str, str]]:
        current = await self.snapshot()
        changes: list[ProductChanged] = []
        for source_id, content_hash in current.items():
            if source_id not in previous:
                changes.append(ProductChanged(source_id, "created"))
            elif previous[source_id] != content_hash:
                changes.append(ProductChanged(source_id, "updated"))
        for source_id in previous:
            if source_id not in current:
                changes.append(ProductChanged(source_id, "deleted"))
        return changes, current
