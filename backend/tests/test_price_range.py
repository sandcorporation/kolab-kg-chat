"""이슈 03 — GraphStore.price_range: 변형 가격 최저·최고 집계(가격 없는 변형 제외)."""
from datetime import datetime, timezone

from apps.connectors.base import ProductDocument, SourceVariant
from apps.graph.store import GraphStore


def _doc(source_id: str, prices: list[int | None]) -> ProductDocument:
    variants = [SourceVariant(str(i), f"opt{i}", p, {}) for i, p in enumerate(prices)]
    return ProductDocument(
        source_id=source_id, name="테스트 상품", brand="B", category_path=["lab"],
        description_text="", images=[], variants=variants,
        content_hash="h", raw={}, fetched_at=datetime.now(timezone.utc),
    )


async def _store() -> GraphStore:
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    return store


async def test_price_range_returns_min_and_max():
    store = await _store()
    await store.upsert_product(_doc("p1", [15800, 32900, 288750]))
    assert await store.price_range("p1") == (15800, 288750)


async def test_price_range_skips_variants_without_price():
    store = await _store()
    await store.upsert_product(_doc("p2", [None, 12000, None]))
    assert await store.price_range("p2") == (12000, 12000)


async def test_price_range_none_when_no_prices():
    store = await _store()
    await store.upsert_product(_doc("p3", [None, None]))
    assert await store.price_range("p3") == (None, None)
