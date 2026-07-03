"""IngestRunner — 초기 전체 적재 + 폴링 delta(content-hash 게이팅)."""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore
from apps.sync.runner import IngestRunner, StructuredFieldInfoExtractor

ALL_IDS = {"1712107033", "1548728629", "1667982841", "DLM-4"}


async def _runner():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    runner = IngestRunner(
        store, YoungcartMySQLConnector.from_env(), StructuredFieldInfoExtractor()
    )
    return store, runner


async def test_full_load_ingests_all_products():
    store, runner = await _runner()
    counts = await runner.full_load()

    assert counts.get("created") == 4
    assert {p["source_id"] for p in await store.list_products()} == ALL_IDS


async def test_full_load_respects_limit():
    _, runner = await _runner()
    counts = await runner.full_load(limit=2)
    assert counts.get("created") == 2


async def test_apply_gate_skips_unchanged():
    _, runner = await _runner()
    first = await runner.apply("1548728629")
    assert first == "created"
    again = await runner.apply("1548728629", gate=True)
    assert again == "unchanged"  # 소스 그대로 → content-hash 게이팅


async def test_sync_once_creates_from_empty_graph():
    store, runner = await _runner()
    counts = await runner.sync_once()  # 빈 그래프 기준선 → 전부 created
    assert counts.get("created") == 4
    assert {p["source_id"] for p in await store.list_products()} == ALL_IDS


async def test_sync_once_stable_after_full_load():
    _, runner = await _runner()
    await runner.full_load()
    counts = await runner.sync_once()  # 그래프 == 소스 → 변경 없음
    assert counts == {}


async def test_sync_once_detects_deletion():
    store, runner = await _runner()
    await runner.full_load()
    # 그래프엔 있으나 소스엔 없는 상품 → deleted 로 감지·반영
    await store.upsert_product(_ghost_doc())
    counts = await runner.sync_once()
    assert counts.get("deleted") == 1
    assert await store.get_product("ghost-not-in-source") is None


async def test_sync_once_guards_against_empty_source():
    # 소스가 비면(장애/오설정) 그래프의 상품을 전량 삭제하지 않고 건너뛴다.
    store, runner = await _runner()
    await runner.full_load()

    class EmptyConnector:
        async def iter_product_ids(self, limit=None):
            return
            yield  # pragma: no cover — 빈 async 제너레이터

        async def assemble(self, source_id):
            return None

    empty_runner = IngestRunner(store, EmptyConnector(), StructuredFieldInfoExtractor())
    counts = await empty_runner.sync_once()

    assert "skipped_empty_source" in counts
    assert {p["source_id"] for p in await store.list_products()} == ALL_IDS  # 삭제 안 됨


def _ghost_doc():
    from datetime import datetime, timezone

    from apps.connectors.base import ProductDocument

    return ProductDocument(
        source_id="ghost-not-in-source",
        name="Ghost",
        brand="",
        category_path=[],
        description_text="",
        images=[],
        variants=[],
        content_hash="ghost-hash",
        raw={},
        fetched_at=datetime.now(timezone.utc),
    )
