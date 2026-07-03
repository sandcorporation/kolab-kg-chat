"""이슈 05 — changed_since(it_update_time) + SyncWatermark."""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.sync.watermark import SyncWatermark

BASELINE = "2026-01-01 00:00:00"


async def _bump(connector, source_id, when):
    conn = await connector._connect()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE g5_shop_item SET it_update_time = %s WHERE it_id = %s", (when, source_id)
            )
        await conn.commit()
    finally:
        conn.close()


async def test_changed_since_returns_only_bumped():
    connector = YoungcartMySQLConnector.from_env()
    await _bump(connector, "DLM-4", BASELINE)  # 원복(다른 테스트 격리)
    # baseline 이후 변경 없음
    assert [sid async for sid in connector.changed_since(BASELINE)] == []

    await _bump(connector, "DLM-4", "2026-02-01 00:00:00")
    try:
        changed = [sid async for sid in connector.changed_since(BASELINE)]
        assert changed == ["DLM-4"]
    finally:
        await _bump(connector, "DLM-4", BASELINE)  # 원복


async def test_latest_update_time_reports_max():
    connector = YoungcartMySQLConnector.from_env()
    await _bump(connector, "DLM-4", "2026-03-15 12:00:00")
    try:
        assert await connector.latest_update_time() == "2026-03-15 12:00:00"
    finally:
        await _bump(connector, "DLM-4", BASELINE)


async def test_watermark_roundtrip_and_persistence():
    wm = SyncWatermark()
    await wm.set("kolab:it_update_time", "2026-01-02 03:04:05")
    assert await wm.get("kolab:it_update_time") == "2026-01-02 03:04:05"
    # 새 인스턴스(재시작 시뮬레이션)에서도 유지
    assert await SyncWatermark().get("kolab:it_update_time") == "2026-01-02 03:04:05"
    assert await wm.get("missing-key", default="X") == "X"
