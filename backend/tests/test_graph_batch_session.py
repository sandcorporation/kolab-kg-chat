"""이슈 03 — GraphStore 배치 세션: 커넥션 재사용 + 배치 커밋."""
from apps.core.db import connect as real_connect
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore


class CountingConnect:
    """열린 커넥션 수를 센다(최적화 계약 검증용)."""

    def __init__(self):
        self.opens = 0

    async def __call__(self, **kwargs):
        self.opens += 1
        return await real_connect(**kwargs)


async def _docs():
    connector = YoungcartMySQLConnector.from_env()
    return [await connector.assemble(sid) async for sid in connector.iter_product_ids()]


async def test_batch_opens_one_connection_for_whole_batch():
    counter = CountingConnect()
    store = GraphStore(connect_factory=counter, graph_name="kg_test")
    await store.reset()
    docs = await _docs()

    counter.opens = 0
    async with store.batch():
        for doc in docs:
            await store.upsert_product(doc)                       # 여러 cypher
            await store.set_attributes(doc.source_id, [
                {"name": "brand", "value": doc.brand, "provenance": "structured",
                 "confidence": 1.0, "is_candidate": True},
            ])
    # 상품 4건 × (upsert + set_attributes)인데도 커넥션은 배치당 1회
    assert counter.opens == 1


async def test_batch_commit_persists_data():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    docs = await _docs()

    async with store.batch():
        for doc in docs:
            await store.upsert_product(doc)

    # 커밋 후 다른 커넥션(단건 조회)에서도 보인다
    assert len({p["source_id"] for p in await store.list_products()}) == 4


async def test_single_ops_still_work_without_batch():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    doc = (await _docs())[0]
    await store.upsert_product(doc)  # 세션 밖 단건도 그대로 동작
    assert await store.get_product(doc.source_id) is not None
