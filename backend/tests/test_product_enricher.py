"""이슈 01 — ProductEnricher: url/image/grounding 결정적 부착."""
from datetime import datetime, timezone

from apps.agent.enricher import ProductEnricher
from apps.connectors.base import ProductDocument, SourceVariant
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore


def _priced_doc(source_id: str, prices: list[int | None]) -> ProductDocument:
    return ProductDocument(
        source_id=source_id, name="비커", brand="B", category_path=[], description_text="",
        images=[], variants=[SourceVariant(str(i), f"o{i}", p, {}) for i, p in enumerate(prices)],
        content_hash="h", raw={}, fetched_at=datetime.now(timezone.utc),
    )


async def _store_with_flask():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    doc = await YoungcartMySQLConnector.from_env().assemble("1548728629")
    await store.upsert_product(doc)
    await store.set_attributes("1548728629", [
        {"name": "material", "value": "glass_borosilicate",
         "provenance": "structured", "confidence": 1.0, "is_candidate": False},
    ])
    return store


async def test_enrich_attaches_url_image_grounding():
    store = await _store_with_flask()
    cards = await ProductEnricher(store).enrich(["1548728629"])

    assert len(cards) == 1
    card = cards[0]
    assert card["url"] == "https://www.kolabshop.com/shop/item.php?it_id=1548728629"
    assert card["image_url"] == "https://img.test/flask/main.jpg"  # 정규화된 첫 이미지
    assert card["name"].startswith("Volumetric Flask")
    assert any(g["name"] == "material" and g["provenance"] == "structured" for g in card["grounding"])


async def test_enrich_skips_missing_ids():
    store = await _store_with_flask()
    cards = await ProductEnricher(store).enrich(["1548728629", "does-not-exist"])
    assert [c["source_id"] for c in cards] == ["1548728629"]


async def test_enrich_attaches_price_range():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    await store.upsert_product(_priced_doc("pr1", [10000, 25000]))
    card = (await ProductEnricher(store).enrich(["pr1"]))[0]
    assert card["price_min"] == 10000
    assert card["price_max"] == 25000


async def test_enrich_price_none_when_no_prices():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    await store.upsert_product(_priced_doc("pr2", [None]))
    card = (await ProductEnricher(store).enrich(["pr2"]))[0]
    assert card["price_min"] is None
    assert card["price_max"] is None
