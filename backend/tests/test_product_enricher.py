"""ADR-0016 — ProductEnricher: 소스 하이드레이션 문서에 url/image/price/grounding 부착."""
from datetime import datetime, timezone

from apps.agent.enricher import ProductEnricher
from apps.connectors.base import ProductDocument, SourceImage, SourceVariant
from apps.extraction.extractor import ExtractedAttribute, ExtractionResult


def _doc(source_id: str, *, prices=(), images=()) -> ProductDocument:
    return ProductDocument(
        source_id=source_id, name="비커", brand="B", category_path=[], description_text="",
        images=[SourceImage(url=u, position=i + 1, source="gallery") for i, u in enumerate(images)],
        variants=[SourceVariant(str(i), f"o{i}", p, {}) for i, p in enumerate(prices)],
        content_hash="h", raw={}, fetched_at=datetime.now(timezone.utc),
    )


class _FakeConnector:
    def __init__(self, *docs: ProductDocument):
        self._docs = {d.source_id: d for d in docs}

    async def assemble_many(self, ids):
        return {i: self._docs[i] for i in ids if i in self._docs}


class _FakeExtractor:
    def __init__(self, attrs_by_id=None):
        self._a = attrs_by_id or {}

    async def extract(self, doc):
        return ExtractionResult(product_type="beaker", attributes=self._a.get(doc.source_id, []))


def _enricher(conn, attrs=None) -> ProductEnricher:
    return ProductEnricher(conn, _FakeExtractor(attrs))


async def test_enrich_attaches_url_image_grounding():
    doc = _doc("1548728629", images=["https://img.test/flask/main.jpg"])
    attrs = {"1548728629": [
        ExtractedAttribute("material", "glass_borosilicate", "structured", 1.0, False),
    ]}
    cards = await _enricher(_FakeConnector(doc), attrs).enrich(["1548728629"])

    assert len(cards) == 1
    card = cards[0]
    assert card["url"] == "https://www.kolabshop.com/shop/item.php?it_id=1548728629"
    assert card["image_url"] == "https://img.test/flask/main.jpg"  # 하이드레이션한 첫 이미지
    assert card["name"] == "비커"
    assert any(g["name"] == "material" and g["provenance"] == "structured" for g in card["grounding"])


async def test_enrich_skips_missing_ids():
    doc = _doc("1548728629")
    cards = await _enricher(_FakeConnector(doc)).enrich(["1548728629", "does-not-exist"])
    assert [c["source_id"] for c in cards] == ["1548728629"]


async def test_enrich_attaches_price_range():
    doc = _doc("pr1", prices=[10000, 25000])
    card = (await _enricher(_FakeConnector(doc)).enrich(["pr1"]))[0]
    assert card["price_min"] == 10000
    assert card["price_max"] == 25000


async def test_enrich_price_none_when_no_prices():
    doc = _doc("pr2", prices=[None])
    card = (await _enricher(_FakeConnector(doc)).enrich(["pr2"]))[0]
    assert card["price_min"] is None
    assert card["price_max"] is None
