"""이슈 07 — 워커 증분 + 재조정 + 폴백."""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore
from apps.sync.runner import WATERMARK_KEY, IngestRunner, StructuredFieldInfoExtractor
from apps.sync.watermark import SyncWatermark

BASELINE = "2026-01-01 00:00:00"


async def _runner():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    connector = YoungcartMySQLConnector.from_env()
    runner = IngestRunner(store, connector, StructuredFieldInfoExtractor())
    await runner.full_load()
    return store, connector, runner


async def _bump(connector, sid, when, name=None):
    conn = await connector._connect()
    try:
        async with conn.cursor() as cur:
            if name is not None:
                await cur.execute(
                    "UPDATE g5_shop_item SET it_name=%s, it_update_time=%s WHERE it_id=%s",
                    (name, when, sid),
                )
            else:
                await cur.execute(
                    "UPDATE g5_shop_item SET it_update_time=%s WHERE it_id=%s", (when, sid)
                )
        await conn.commit()
    finally:
        conn.close()


async def test_incremental_processes_only_changed_and_advances_watermark():
    store, connector, runner = await _runner()
    wm = SyncWatermark()
    await wm.set(WATERMARK_KEY, BASELINE)

    # 변경 없음 → 처리 0
    assert await runner.sync_incremental(wm) == {}

    # DLM-4를 실제 변경(이름) + it_update_time 상향 → 그 상품만 updated
    original = "Deuterium oxide (D, 99.9%) 중수소수"
    await _bump(connector, "DLM-4", "2026-02-01 00:00:00", name="D2O CHANGED")
    try:
        counts = await runner.sync_incremental(wm)
        assert counts.get("updated") == 1
        assert await wm.get(WATERMARK_KEY) == "2026-02-01 00:00:00"  # watermark 전진
    finally:
        await _bump(connector, "DLM-4", BASELINE, name=original)


async def test_reconcile_detects_deletion():
    store, connector, runner = await _runner()
    # 그래프엔 있으나 소스엔 없는 유령 상품 주입 → 재조정이 제거
    from datetime import datetime, timezone

    from apps.connectors.base import ProductDocument

    ghost = ProductDocument(
        source_id="ghost-x", name="G", brand="", category_path=[], description_text="",
        images=[], variants=[], content_hash="h", raw={}, fetched_at=datetime.now(timezone.utc),
    )
    await store.upsert_product(ghost)
    counts = await runner.sync_once()
    assert counts.get("deleted") == 1
    assert await store.get_product("ghost-x") is None


async def test_incremental_falls_back_when_no_update_time():
    store, _, runner = await _runner()

    class NoTimestampConnector:
        async def latest_update_time(self):
            return None  # it_update_time 컬럼 부재

    runner._connector = NoTimestampConnector()
    counts = await runner.sync_incremental(SyncWatermark())
    assert counts == {"incremental_unavailable": 1}  # 워커가 재조정으로 폴백할 신호
