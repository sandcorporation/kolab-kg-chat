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


async def test_assemble_excludes_addon_options():
    # io_type=1 부가옵션(교정성적서 5000원)은 변형·최저가에서 제외 — 최저가는 실제 변형가여야.
    doc = await _connector().assemble("1548728629")
    catnos = {v.raw.get("catalog_number") for v in doc.variants}
    assert "CAL-CERT" not in catnos                        # 부가옵션은 변형이 아님
    assert min(v.price for v in doc.variants) == 13400      # 성적서 5000이 최저가로 안 튐


async def test_assemble_excludes_soldout_options():
    # io_stock_qty<=0 품절 옵션(SOLDOUT-VAR 8000원)은 변형·최저가에서 제외.
    doc = await _connector().assemble("1548728629")
    catnos = {v.raw.get("catalog_number") for v in doc.variants}
    assert "SOLDOUT-VAR" not in catnos
    assert min(v.price for v in doc.variants) == 13400      # 8000 품절이 최저가로 안 튐


async def test_assemble_flags_soldout_item():
    # it_soldout=1 상품(SOLD-1)은 추천 가능하되 soldout=True로 표시(안내 메시지용).
    doc = await _connector().assemble("SOLD-1")
    assert doc is not None and doc.soldout is True


async def test_assemble_available_product_not_soldout():
    # 구매 가능한 변형이 있는 상품(flask)은 soldout=False.
    doc = await _connector().assemble("1548728629")
    assert doc.soldout is False


async def test_variant_price_is_absolute():
    doc = await _connector().assemble("1667982841")  # 점도계
    prices = {v.raw["catalog_number"]: v.price for v in doc.variants}
    assert prices["ATAGO6840"] == 3630000
    assert prices["ATAGO6865"] == 6182000  # io_price는 절대가(실제 스키마)


async def test_category_path_is_codes():
    # 실제 덤프엔 카테고리 이름 테이블이 없어 ca_id 코드만 보존한다.
    doc = await _connector().assemble("1548728629")
    assert doc.category_path == ["20", "2010"]


async def test_iter_product_ids_includes_soldout():
    # 품절 상품(SOLD-1)도 적재·추천 대상에 포함된다(추천 시 안내 메시지로 처리).
    ids = [pid async for pid in _connector().iter_product_ids()]
    assert set(ids) == {"1712107033", "1548728629", "1667982841", "DLM-4", "SOLD-1"}


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


async def test_sample_diverse_includes_keyword_matches_and_dedupes():
    # 유형 키워드로 계층 샘플링 — flask는 Volumetric Flask를 포함하고, 나머지는 랜덤으로 채운다.
    c = _connector()
    ids = await c.sample_diverse_ids(["flask"], per_keyword=5, target=4)
    assert "1548728629" in ids                 # Volumetric Flask가 flask 키워드로 포함
    assert len(ids) == len(set(ids))           # 중복 없음
    assert len(ids) <= 4                        # target 상한 준수


async def test_sample_diverse_respects_target():
    c = _connector()
    ids = await c.sample_diverse_ids(["flask", "viscometer"], per_keyword=5, target=2)
    assert len(ids) == 2


async def test_content_hash_pdf_url_is_backward_compatible():
    # pdf_url 없는(빈) 상품은 기존 해시와 바이트 동일 → 재처리 0. 있으면 달라짐.
    from apps.connectors.youngcart_mysql import _content_hash

    base = _content_hash("N", "B", [], "", [], [])
    same = _content_hash("N", "B", [], "", [], [], "")
    diff = _content_hash("N", "B", [], "", [], [], "http://x/spec.pdf")
    assert same == base            # 빈 pdf_url → 하위호환(캐시 유지)
    assert diff != base            # pdf_url 존재 → 재처리 유도


async def test_assembled_product_has_empty_pdf_url_without_column():
    # mock 소스엔 it_pdf_url 컬럼이 없으므로 pdf_url은 ""(해시 불변)
    doc = await _connector().assemble("1548728629")
    assert doc.pdf_url == ""


def test_clean_brand_preserves_real_names():
    from apps.connectors.youngcart_mysql import _clean_brand

    assert _clean_brand("ALDRICH") == "ALDRICH"
    assert _clean_brand("  SIGMA ") == "SIGMA"       # 공백 정리
    assert _clean_brand("3M") == "3M"                # 숫자 포함이지만 정상 브랜드 → 보존


def test_clean_brand_drops_numeric_and_empty():
    from apps.connectors.youngcart_mysql import _clean_brand

    assert _clean_brand("7") is None                 # 순수 숫자 코드 오염(비이커집게) → 무효
    assert _clean_brand("325") is None               # it_maker 코드류 → 무효
    assert _clean_brand("") is None
    assert _clean_brand(None) is None


async def test_sample_by_category_all_when_under_cap():
    # 카테고리 20(1548728629·SOLD-1)·30(2)·40(1) 각 ≤3 → 전부(품절 SOLD-1 포함)
    ids = await _connector().sample_by_category_ids(per_category=3)
    assert set(ids) == {"1548728629", "1667982841", "1712107033", "DLM-4", "SOLD-1"}


async def test_sample_by_category_caps_per_category():
    # 카테고리당 1개 → 3개(ca_id 30은 it_id 작은 1667982841)
    ids = await _connector().sample_by_category_ids(per_category=1)
    assert set(ids) == {"1548728629", "1667982841", "DLM-4"}
