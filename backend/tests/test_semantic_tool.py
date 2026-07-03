"""이슈 02 — Recommendation Agent에 semantic_search 도구 배선(ADR-0012)."""
from langchain_core.messages import AIMessage

from apps.agent.recommendation_agent import RecommendationAgent
from apps.agent.tools import GraphTools
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore
from tests.fake_chat import ScriptedChatModel


class FakeSemantic:
    async def search(self, keyword, k=10):
        return [{"source_id": "1548728629", "name": "flask"}]


async def _tools():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    doc = await YoungcartMySQLConnector.from_env().assemble("1548728629")
    await store.upsert_product(doc)
    return GraphTools(store)


async def test_agent_can_call_semantic_search():
    tools = await _tools()
    model = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "semantic_search", "args": {"keyword": "유리 용기", "k": 5}, "id": "c1"}]),
        AIMessage(content="", tool_calls=[{
            "name": "recommend", "args": {"ids": ["1548728629"]}, "id": "c2"}]),
        AIMessage(content="붕규산 유리라 추천합니다."),
    ])
    agent = RecommendationAgent(model, tools, semantic_tool=FakeSemantic())

    result = await agent.run("유리 용기 비슷한 거")

    assert result.recommended_ids == ["1548728629"]
    assert "추천" in result.rationale


async def test_agent_works_without_semantic_tool():
    # semantic_tool 미주입 시에도 기존 그래프 도구만으로 정상 동작(회귀 없음).
    tools = await _tools()
    agent = RecommendationAgent(ScriptedChatModel(responses=[AIMessage(content="답변")]), tools)
    res = await agent.run("아무거나")
    assert res.recommended_ids == []
    assert res.rationale == "답변"
