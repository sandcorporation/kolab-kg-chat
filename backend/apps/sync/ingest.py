"""수집 트레이서 (이슈 07) — SourceConnector → GraphStore.

소스(MySQL)에서 ProductDocument를 끌어와 그래프에 upsert하는 최소 파이프라인.
SyncOrchestrator(이슈 13/14)가 이 위에 큐·코얼레싱·content-hash 게이팅을 얹는다.
"""
from __future__ import annotations


async def ingest_one(connector, store, source_id: str) -> bool:
    """한 Product를 현재 상태로 반영한다. 소스에 없으면 그래프에서 제거한다(멱등)."""
    doc = await connector.assemble(source_id)
    if doc is None:
        await store.delete_product(source_id)
        return False
    await store.upsert_product(doc)
    return True


async def ingest_all(connector, store) -> int:
    """초기 전체 적재 — 소스의 모든 Product를 그래프에 반영하고 처리 건수를 반환한다."""
    count = 0
    async for source_id in connector.iter_product_ids():
        if await ingest_one(connector, store, source_id):
            count += 1
    return count
