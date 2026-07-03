"""이슈 01 — AGE 속성 인덱스 멱등 생성."""
from apps.graph.store import GraphStore

EXPECTED = {"ix_product_source_id", "ix_variant_variant_key", "ix_attribute_name", "ix_attribute_value"}


async def test_ensure_indexes_creates_property_indexes():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    await store.ensure_indexes()  # 빈 그래프에서도 라벨 생성 후 인덱스
    assert EXPECTED <= set(await store.index_names())


async def test_ensure_indexes_is_idempotent():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    await store.ensure_indexes()
    await store.ensure_indexes()  # 두 번째도 오류 없음
    assert EXPECTED <= set(await store.index_names())
