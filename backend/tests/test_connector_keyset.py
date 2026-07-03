"""이슈 04 — Source Connector 키셋 스트리밍 + 커넥션 재사용."""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector

ALL_IDS = {"1712107033", "1548728629", "1667982841", "DLM-4"}


async def test_iter_yields_all_ids_no_dup():
    connector = YoungcartMySQLConnector.from_env()
    ids = [sid async for sid in connector.iter_product_ids()]
    assert set(ids) == ALL_IDS
    assert len(ids) == len(set(ids))  # 중복 없음


async def test_iter_small_page_still_yields_all():
    # 키셋 청크가 작아도(페이지 경계 여럿) 전량을 순서대로 산출
    connector = YoungcartMySQLConnector.from_env()
    ids = [sid async for sid in connector.iter_product_ids(page_size=1)]
    assert set(ids) == ALL_IDS
    assert ids == sorted(ids)  # it_id 오름차순


async def test_iter_respects_limit():
    connector = YoungcartMySQLConnector.from_env()
    ids = [sid async for sid in connector.iter_product_ids(limit=2, page_size=1)]
    assert len(ids) == 2


async def test_session_reuses_one_source_connection():
    connector = YoungcartMySQLConnector.from_env()
    opens = {"n": 0}
    orig = connector._connect

    async def counting():
        opens["n"] += 1
        return await orig()

    connector._connect = counting

    async with connector.session():
        ids = [sid async for sid in connector.iter_product_ids(page_size=2)]
        for sid in ids:
            await connector.assemble(sid)
    # iter(여러 청크) + assemble 4회인데도 소스 커넥션은 세션 1회
    assert opens["n"] == 1
