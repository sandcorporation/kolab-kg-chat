"""이슈 04 — SourceConnector(영카트 MySQL) → ProductDocument.

Mock Source DB 대상 통합 테스트. 행동(row → ProductDocument)만 검증한다.
"""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector


def _connector() -> YoungcartMySQLConnector:
    return YoungcartMySQLConnector.from_env()


async def test_assemble_flask_has_19_variants():
    doc = await _connector().assemble("1548728629")
    assert doc is not None
    assert doc.name.startswith("Volumetric Flask")
    assert doc.brand == "ISOLAB"
    assert len(doc.variants) == 19


async def test_variant_price_is_absolute():
    doc = await _connector().assemble("1667982841")  # 점도계
    prices = {v.raw["catalog_number"]: v.price for v in doc.variants}
    assert prices["ATAGO6840"] == 3630000
    assert prices["ATAGO6865"] == 6182000  # io_price는 절대가(실제 스키마)


async def test_category_path_is_codes():
    # 실제 덤프엔 카테고리 이름 테이블이 없어 ca_id 코드만 보존한다.
    doc = await _connector().assemble("1548728629")
    assert doc.category_path == ["20", "2010"]


async def test_iter_product_ids_yields_all_four():
    ids = [pid async for pid in _connector().iter_product_ids()]
    assert set(ids) == {"1712107033", "1548728629", "1667982841", "DLM-4"}


async def test_assemble_is_deterministic():
    connector = _connector()
    first = await connector.assemble("DLM-4")
    second = await connector.assemble("DLM-4")
    assert first.content_hash == second.content_hash


async def test_missing_product_returns_none():
    assert await _connector().assemble("does-not-exist") is None


async def test_description_text_is_plain_text():
    doc = await _connector().assemble("1548728629")
    assert "<" not in doc.description_text and ">" not in doc.description_text
    assert "유리" in doc.description_text  # 내용은 보존


async def test_viscometer_collects_spec_images():
    doc = await _connector().assemble("1667982841")
    assert len(doc.images) >= 3  # main + spec1 + spec2 + dim
    assert doc.images[0].position == 1


async def test_assemble_many_matches_single():
    # 배치 하이드레이션(WHERE it_id IN ...)은 개별 assemble과 동일 문서를 낸다(인덱스 친화).
    c = _connector()
    many = await c.assemble_many(["1548728629", "1667982841"])
    assert set(many.keys()) == {"1548728629", "1667982841"}
    single = await c.assemble("1548728629")
    assert many["1548728629"].content_hash == single.content_hash
    visc = await c.assemble("1667982841")
    assert many["1667982841"].content_hash == visc.content_hash


async def test_assemble_many_omits_missing_and_empty():
    c = _connector()
    assert await c.assemble_many([]) == {}
    got = await c.assemble_many(["DLM-4", "does-not-exist"])
    assert set(got.keys()) == {"DLM-4"}
