"""이슈 07 — 수집 트레이서: MySQL → 그래프 전 구간 1회 관통."""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore
from apps.sync.ingest import ingest_all, ingest_one


def _store() -> GraphStore:
    return GraphStore(graph_name="kg_test")


def _connector() -> YoungcartMySQLConnector:
    return YoungcartMySQLConnector.from_env()


async def test_ingest_all_flows_source_to_graph():
    store = _store()
    await store.reset()

    count = await ingest_all(_connector(), store)
    assert count == 4

    products = await store.list_products()
    assert {p["source_id"] for p in products} == {
        "1712107033",
        "1548728629",
        "1667982841",
        "DLM-4",
    }
    # 메스플라스크 19 변형이 HAS_VARIANT로 연결됨
    flask = await store.get_product("1548728629")
    assert flask["variant_count"] == 19


async def test_ingest_one_deletes_when_source_missing():
    store = _store()
    await store.reset()
    connector = _connector()

    assert await ingest_one(connector, store, "DLM-4") is True
    assert await store.get_product("DLM-4") is not None

    assert await ingest_one(connector, store, "does-not-exist") is False
    assert await store.get_product("does-not-exist") is None
