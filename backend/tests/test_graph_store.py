"""이슈 06 — GraphStore: AGE 위 Product/Variant 멱등 upsert.

실제 Postgres+AGE 컨테이너 대상. 외부 행동(upsert→read-back)만 검증한다.
"""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore


def _store() -> GraphStore:
    return GraphStore(graph_name="kg_test")


def _connector() -> YoungcartMySQLConnector:
    return YoungcartMySQLConnector.from_env()


async def test_upsert_creates_product_with_variants():
    store = _store()
    await store.reset()
    doc = await _connector().assemble("1548728629")
    await store.upsert_product(doc)

    product = await store.get_product("1548728629")
    assert product is not None
    assert product["name"].startswith("Volumetric Flask")
    assert product["brand"] == "ISOLAB"
    assert product["variant_count"] == 19


async def test_upsert_is_idempotent():
    store = _store()
    await store.reset()
    doc = await _connector().assemble("1548728629")
    await store.upsert_product(doc)
    await store.upsert_product(doc)

    products = await store.list_products()
    matching = [p for p in products if p["source_id"] == "1548728629"]
    assert len(matching) == 1            # 노드 중복 없음
    assert matching[0]["variant_count"] == 19  # 변형 중복 없음


async def test_delete_removes_product():
    store = _store()
    await store.reset()
    doc = await _connector().assemble("DLM-4")
    await store.upsert_product(doc)
    await store.delete_product("DLM-4")

    assert await store.get_product("DLM-4") is None


async def test_upsert_all_four_products():
    store = _store()
    await store.reset()
    connector = _connector()
    async for pid in connector.iter_product_ids():
        await store.upsert_product(await connector.assemble(pid))

    products = await store.list_products()
    assert {p["source_id"] for p in products} == {
        "1712107033",
        "1548728629",
        "1667982841",
        "DLM-4",
    }
