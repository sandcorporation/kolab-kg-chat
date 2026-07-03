"""이슈 01 — ProductEnricher: url/image/grounding 결정적 부착."""
from apps.agent.enricher import ProductEnricher
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore


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
