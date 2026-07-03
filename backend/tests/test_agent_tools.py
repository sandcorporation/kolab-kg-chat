"""이슈 02 — Agent Tools: 그래프 위 결정적 도구."""
from apps.agent.tools import GraphTools
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore


async def _tools_with_data():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    connector = YoungcartMySQLConnector.from_env()
    flask = await connector.assemble("1548728629")
    await store.upsert_product(flask)
    await store.set_attributes("1548728629", [
        {"name": "material", "value": "glass_borosilicate",
         "provenance": "structured", "confidence": 1.0, "is_candidate": False},
    ])
    await store.add_compatibility("1548728629", "DLM-4")
    return GraphTools(store)


async def test_search_products_by_name_keyword():
    tools = await _tools_with_data()
    hits = await tools.search_products("flask")
    names = {h["name"] for h in hits}
    assert any("Flask" in n or "플라스크" in n for n in names)


async def test_search_products_tokenizes_phrase_or_match():
    # 구절이어도 토큰 OR 매칭 — 'borosilicate'는 없지만 'flask'가 이름에 걸린다.
    tools = await _tools_with_data()
    hits = await tools.search_products("borosilicate flask")
    assert any("Flask" in h["name"] for h in hits)


async def test_find_products_by_condition():
    tools = await _tools_with_data()
    ids = await tools.find_products([{"name": "material", "op": "==", "value": "glass_borosilicate"}])
    assert "1548728629" in ids


async def test_find_compatible_traverses():
    tools = await _tools_with_data()
    compatible = await tools.find_compatible("1548728629", depth=2)
    assert "DLM-4" in {c["source_id"] for c in compatible}


async def test_get_attributes_returns_grounding():
    tools = await _tools_with_data()
    attrs = await tools.get_attributes("1548728629")
    assert any(a["name"] == "material" for a in attrs)

# 추천 포착은 GraphTools 사이드채널에서 그래프 state(Command)로 이동했다.
# 관련 검증은 test_recommendation_agent(astream result·동시성 격리)로 이관됨.
