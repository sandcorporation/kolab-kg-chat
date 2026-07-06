"""Agent runtime — 미설정 시 폴백 컨텍스트 조립(ADR-0016, C: 소스 하이드레이션)."""
from apps.agent.enricher import ProductEnricher
from apps.agent.rag import RagRecommender
from apps.agent.runtime import build_default_context


def test_default_context_wires_rag_and_enricher():
    # 우리 DB(임베딩·설명) 위 RAG 추천기 + 소스 하이드레이션 ProductEnricher 조립(네트워크 없음)
    context = build_default_context()
    assert isinstance(context.agent, RagRecommender)
    assert isinstance(context.enricher, ProductEnricher)
