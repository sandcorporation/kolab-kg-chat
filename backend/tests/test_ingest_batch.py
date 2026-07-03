"""이슈 06 — IngestRunner 배치 full_load: 키셋 + 배치 세션 + 배치당 커밋."""
from apps.core.db import connect as real_connect
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore
from apps.sync.runner import IngestRunner, StructuredFieldInfoExtractor

ALL_IDS = {"1712107033", "1548728629", "1667982841", "DLM-4"}


class CountingConnect:
    def __init__(self):
        self.opens = 0

    async def __call__(self, **kwargs):
        self.opens += 1
        return await real_connect(**kwargs)


def _runner(store):
    return IngestRunner(store, YoungcartMySQLConnector.from_env(), StructuredFieldInfoExtractor())


async def test_batched_full_load_ingests_all_and_idempotent():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    counts = await _runner(store).full_load(batch_size=2)
    assert counts.get("created") == 4
    assert {p["source_id"] for p in await store.list_products()} == ALL_IDS

    # 재실행 멱등(중복 없음, 갱신으로 반영)
    counts2 = await _runner(store).full_load(batch_size=2)
    assert counts2.get("updated") == 4
    assert len(await store.list_products()) == 4


async def test_full_load_commits_per_batch_not_per_product():
    counter = CountingConnect()
    store = GraphStore(connect_factory=counter, graph_name="kg_test")
    await store.reset()
    counter.opens = 0
    await _runner(store).full_load(batch_size=2)  # 4개 → 2배치
    # ensure_indexes(1) + 배치 2회(각 1) = 3. 상품마다 커넥션을 열지 않는다.
    assert counter.opens == 3
