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
    """E2E/데모용 결정적 에이전트(AGENT_FAKE=1). OpenAI 없이 카탈로그 상위 상품을 추천한다."""

    def __init__(self, store):
        self._store = store

    async def astream(self, query: str):
        rationale = (
            f"'{query}' 요청을 확인했습니다. 카탈로그에서 조건에 부합하는 상품을 골라 "
            "재질·규격 등 확인된 속성을 근거로 아래와 같이 추천드립니다."
        )
        for word in rationale.split(" "):
            yield {"type": "token", "content": word + " "}
        products = await self._store.list_products()
        # 근거(속성)가 있는 상품을 우선 추천해 카드에 grounding이 보이도록 한다.
        picked: list[str] = []
        for p in products:
            if await self._store.get_attributes(p["source_id"]):
                picked.append(p["source_id"])
            if len(picked) >= 3:
                break
        if not picked:
            picked = [p["source_id"] for p in products[:3]]
        yield {"type": "result", "recommended_ids": picked}


def build_default_context(graph_name: str = "knowledge_graph") -> AgentContext:
    """실제 경로: 운영 그래프 위에 RAG 추천기 + ProductEnricher를 조립한다(ADR-0014).

    AGENT_FAKE=1이면 OpenAI 대신 결정적 스크립트 에이전트를 쓴다(E2E/키 없는 데모).
    """
    import os

    from apps.agent.enricher import ProductEnricher
    from apps.graph.store import GraphStore

    store = GraphStore(graph_name=graph_name)
    enricher = ProductEnricher(store)

    if os.environ.get("AGENT_FAKE"):
        return AgentContext(agent=ScriptedStreamAgent(store), enricher=enricher)

    # RAG 읽기 경로(ADR-0014): 질의이해 → 키워드∪시맨틱 → LLM 읽기·선택. 도구 루프 없음.
    from langchain_openai import ChatOpenAI

    from apps.agent.rag import RagRecommender
    from apps.agent.retrieval import HybridRetriever
    from apps.embeddings.store import SemanticSearch

    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ["OPEN_AI_KEY"], temperature=0,
    )
    retriever = HybridRetriever(store, SemanticSearch())
    agent = RagRecommender(model, retriever)
    return AgentContext(agent=agent, enricher=enricher)
