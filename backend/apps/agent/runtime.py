"""Agent runtime 컨텍스트 (이슈 04) — 엔드포인트가 쓰는 에이전트+엔리처 조립.

테스트는 set_agent_context로 fake 컨텍스트를 주입한다(파이프라인 패턴과 동일).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentContext:
    agent: object   # astream(query)/run(query) 지원
    enricher: object  # enrich(ids) 지원


_context: AgentContext | None = None


def set_agent_context(context: AgentContext | None) -> None:
    global _context
    _context = context


def get_agent_context() -> AgentContext:
    if _context is None:
        raise RuntimeError("agent context is not configured")
    return _context


class ScriptedStreamAgent:
    """E2E/데모용 결정적 에이전트(AGENT_FAKE=1). OpenAI 없이 소스 상위 상품을 추천한다."""

    def __init__(self, connector):
        self._connector = connector

    async def astream(self, query: str):
        rationale = (
            f"'{query}' 요청을 확인했습니다. 카탈로그에서 조건에 부합하는 상품을 골라 "
            "재질·규격 등 확인된 속성을 근거로 아래와 같이 추천드립니다."
        )
        for word in rationale.split(" "):
            yield {"type": "token", "content": word + " "}
        picked: list[str] = [sid async for sid in self._connector.iter_product_ids(limit=3)]
        yield {"type": "result", "recommended_ids": picked}


def build_default_context() -> AgentContext:
    """실제 경로: 우리 DB(임베딩·설명) 위 RAG 추천기 + 소스 하이드레이션 ProductEnricher 조립.

    C(소스 하이드레이션, ADR-0016): 검색은 우리 DB, 상품 사실은 채팅 후반에 소스에서 붙인다.
    AGENT_FAKE=1이면 OpenAI 대신 결정적 스크립트 에이전트를 쓴다(E2E/키 없는 데모).
    """
    import os

    from apps.agent.enricher import ProductEnricher
    from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
    from apps.sync.runner import build_extractor

    connector = YoungcartMySQLConnector.from_env()
    enricher = ProductEnricher(connector, build_extractor(use_llm=False))

    if os.environ.get("AGENT_FAKE"):
        return AgentContext(agent=ScriptedStreamAgent(connector), enricher=enricher)

    # RAG 읽기 경로: 키워드(name)∪시맨틱(임베딩) → LLM 읽기·선택. 질의이해·도구 루프 없음(ADR-0015).
    from langchain_openai import ChatOpenAI

    from apps.agent.query_analyzer import QueryAnalyzer
    from apps.agent.rag import RagRecommender
    from apps.agent.retrieval import HybridRetriever
    from apps.embeddings.describe import DescriptionStore
    from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider, SemanticSearch

    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ["OPEN_AI_KEY"], temperature=0,
    )
    keyword = EmbeddingStore(OpenAIEmbeddingProvider())  # keyword_search(name ILIKE)
    retriever = HybridRetriever(keyword, SemanticSearch(), DescriptionStore())
    analyzer = QueryAnalyzer(model)  # ADR-0017: 질의생성 복구 + 반복 루프 라우팅
    agent = RagRecommender(model, retriever, analyzer)
    return AgentContext(agent=agent, enricher=enricher)
