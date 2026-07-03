"""이슈 03 — RecommendationAgent: langgraph 툴콜 루프."""
from langchain_core.messages import AIMessage

from apps.agent.recommendation_agent import RecommendationAgent
from apps.agent.tools import GraphTools
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore
from tests.fake_chat import ScriptedChatModel


async def _tools_with_data():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    flask = await YoungcartMySQLConnector.from_env().assemble("1548728629")
    await store.upsert_product(flask)
    await store.set_attributes("1548728629", [
        {"name": "material", "value": "glass_borosilicate",
         "provenance": "structured", "confidence": 1.0, "is_candidate": False},
    ])
    return GraphTools(store)


async def test_agent_runs_tool_loop_and_records_recommendation():
    tools = await _tools_with_data()
    model = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "find_products",
            "args": {"conditions": [{"name": "material", "op": "==", "value": "glass_borosilicate"}]},
            "id": "c1",
        }]),
        AIMessage(content="", tool_calls=[{
            "name": "recommend", "args": {"ids": ["1548728629"]}, "id": "c2",
        }]),
        AIMessage(content="붕규산 유리 재질이라 내열성이 좋아 추천합니다."),
    ])

    result = await RecommendationAgent(model, tools).run("내열성 좋은 플라스크 추천해줘")

    assert result.recommended_ids == ["1548728629"]
    assert "붕규산" in result.rationale


async def test_agent_astream_yields_tokens_then_result():
    tools = await _tools_with_data()
    model = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "recommend", "args": {"ids": ["1548728629"]}, "id": "c1",
        }]),
        AIMessage(content="붕규산 유리라 추천합니다."),
    ])

    events = [ev async for ev in RecommendationAgent(model, tools).astream("플라스크")]

    tokens = "".join(ev["content"] for ev in events if ev["type"] == "token")
    result = [ev for ev in events if ev["type"] == "result"][-1]
    assert "붕규산" in tokens
    assert result["recommended_ids"] == ["1548728629"]


async def test_agent_without_tool_calls_returns_rationale_only():
    tools = await _tools_with_data()
    model = ScriptedChatModel(responses=[
        AIMessage(content="죄송하지만 조건에 맞는 상품을 찾지 못했습니다."),
    ])

    result = await RecommendationAgent(model, tools).run("존재하지 않는 조건")

    assert result.recommended_ids == []
    assert "찾지 못했" in result.rationale
