"""Agent runtime — 미설정 시 폴백 컨텍스트 조립(ADR-0011)."""
from apps.agent.enricher import ProductEnricher
from apps.agent.recommendation_agent import RecommendationAgent
from apps.agent.runtime import build_default_context


def test_default_context_wires_agent_and_enricher():
    # 운영 그래프 위 langgraph 에이전트 + ProductEnricher 조립(네트워크 없음)
    context = build_default_context(graph_name="kg_test")
    assert isinstance(context.agent, RecommendationAgent)
    assert isinstance(context.enricher, ProductEnricher)
