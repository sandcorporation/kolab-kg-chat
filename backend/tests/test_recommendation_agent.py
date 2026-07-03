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


async def test_concurrent_runs_do_not_share_recommendations():
    # 같은 GraphTools를 공유하는 두 에이전트가 동시에 서로 다른 추천을 해도 섞이지 않는다
    # (추천 포착이 공유 사이드채널이 아니라 요청별 그래프 state이므로).
    import asyncio

    tools = await _tools_with_data()

    def agent_for(sid):
        model = ScriptedChatModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "recommend", "args": {"ids": [sid]}, "id": "c1"}]),
            AIMessage(content=f"{sid} 추천합니다."),
        ])
        return RecommendationAgent(model, tools)

    async def collect(agent, q):
        events = [e async for e in agent.astream(q)]
        return [e for e in events if e["type"] == "result"][-1]["recommended_ids"]

    ra, rb = await asyncio.gather(
        collect(agent_for("1548728629"), "A"),
        collect(agent_for("9999999999"), "B"),
    )
    assert ra == ["1548728629"]
    assert rb == ["9999999999"]


async def test_agent_astream_emits_status_before_tokens_on_tool_call():
    # 도구 호출(find_products)은 매핑된 한글 라벨 status로 알려지고, 토큰보다 먼저 온다.
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
        AIMessage(content="붕규산 유리라 추천합니다."),
    ])

    events = [ev async for ev in RecommendationAgent(model, tools).astream("플라스크")]
    types = [ev["type"] for ev in events]
    labels = [ev["label"] for ev in events if ev["type"] == "status"]

    assert "상품 검색 중…" in labels          # find_products → 매핑 라벨
    assert "추천 정리 중…" in labels          # recommend → 매핑 라벨
    assert types.index("status") < types.index("token")  # status가 토큰보다 앞


async def test_agent_without_tool_calls_returns_rationale_only():
    tools = await _tools_with_data()
    model = ScriptedChatModel(responses=[
        AIMessage(content="죄송하지만 조건에 맞는 상품을 찾지 못했습니다."),
    ])

    result = await RecommendationAgent(model, tools).run("존재하지 않는 조건")

    assert result.recommended_ids == []
    assert "찾지 못했" in result.rationale
