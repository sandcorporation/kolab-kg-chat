"""이슈 01 (ADR-0018) — 필터 파서 + 레지스트리 추출."""
from datetime import datetime, timezone

from apps.connectors.base import ProductDocument, SourceVariant
from apps.embeddings.filters import extract_filters, parse_range, parse_storage_temp


def test_parse_range_variants():
    assert parse_range("82-86 C (lit.)") == (82.0, 86.0)   # 범위
    assert parse_range(">=99.5% (GC)") == (99.5, 99.5)      # 하나 → point
    assert parse_range("71.08") == (71.08, 71.08)
    assert parse_range("") == (None, None)                   # 없음
    assert parse_range("no digits here") == (None, None)


def test_parse_range_distinguishes_dash_from_negative():
    assert parse_range("2-8C") == (2.0, 8.0)                 # 범위 구분자
    assert parse_range("-20C") == (-20.0, -20.0)             # 음수


def test_parse_storage_temp_vocab():
    assert parse_storage_temp("2-8C") == (2.0, 8.0)
    assert parse_storage_temp("room temperature") == (15.0, 25.0)
    assert parse_storage_temp("protect from light") == (None, None)  # 온도 아님 → 제외


def _doc(source_id, prices=(), field_info=None):
    fi = field_info or {}
    variants = [SourceVariant(str(i), f"o{i}", p, {"field_info": fi} if fi else {})
                for i, p in enumerate(prices)] or [SourceVariant("0", "o", None, {"field_info": fi})]
    return ProductDocument(
        source_id=source_id, name="시약", brand="B", category_path=[], description_text="",
        images=[], variants=variants, content_hash="h", raw={}, fetched_at=datetime.now(timezone.utc))


def test_extract_filters_price_and_specs():
    doc = _doc("p1", prices=[10000, 25000],
               field_info={"purity": ">=99.5% (GC)", "molecular_weight": "71.08", "storage": "2-8C"})
    f = extract_filters(doc)
    assert f["price"] == (10000.0, 25000.0)
    assert f["purity"] == (99.5, 99.5)
    assert f["molecular_weight"] == (71.08, 71.08)
    assert f["storage_temp"] == (2.0, 8.0)


def test_extract_filters_omits_missing():
    doc = _doc("p2", prices=[None])   # 가격·필드 없음
    f = extract_filters(doc)
    assert "price" not in f and "purity" not in f and "storage_temp" not in f


async def test_embed_product_persists_filter_columns():
    from apps.core.db import connect
    from apps.embeddings.store import EmbeddingStore, FakeEmbeddingProvider

    emb = EmbeddingStore(FakeEmbeddingProvider(), table="kg_embedding_test")
    await emb.reset()
    await emb.embed_product("f1", "시약", "시약 text", "h1",
                            filters={"price": (10000.0, 25000.0), "storage_temp": (2.0, 8.0)})
    conn = await connect()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT price_min, price_max, storage_temp_min, storage_temp_max, purity_min "
                "FROM kg_embedding_test WHERE source_id='f1'")
            row = await cur.fetchone()
    finally:
        await conn.close()
    assert row == (10000.0, 25000.0, 2.0, 8.0, None)  # 준 필터는 채워지고 안 준 건 NULL
