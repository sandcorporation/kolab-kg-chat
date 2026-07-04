"""RetrievalConfig (이슈 01) — config_id → 에이전트 컨텍스트(도구·노출 provenance).

2/3/4는 같은 eval_graph를 공유하고 config별로 노출 provenance + 도구를 토글한다.
config 1(SQL)·config 4(semantic_search) 도구는 이슈 02/04에서 얹는다.
"""
from __future__ import annotations

from dataclasses import dataclass

from apps.agent.enricher import ProductEnricher
from apps.agent.recommendation_agent import build_openai_agent
from apps.agent.tools import GraphTools
from apps.graph.store import GraphStore

# config_id → (노출 provenance, semantic_search 사용 여부). config1은 SQL 전용.
CONFIGS: dict[str, dict] = {
    "config1": {"sql": True},
    "config2": {"provenances": {"structured"}, "semantic": False},
    "config3": {"provenances": {"structured", "llm_ocr"}, "semantic": False},
    "config4": {"provenances": {"structured", "llm_ocr"}, "semantic": True},
    "config5": {"hybrid": True},  # 하이브리드 융합 + 리랭킹(에이전트 루프 없음)
    "rag": {"rag": True},         # RAG: 질의이해→키워드∪시맨틱→LLM 읽기·선택(도구 루프 없음)
}


@dataclass
class EvalContext:
    agent: object
    enricher: object


def build_eval_context(config_id: str, graph_name: str = "eval_graph") -> EvalContext:
    spec = CONFIGS[config_id]
    store = GraphStore(graph_name=graph_name)
    enricher = ProductEnricher(store)

    if spec.get("rag"):  # RAG: 질의이해 → 키워드∪시맨틱 → LLM 읽기·선택(도구 루프 없음)
        import os

        from langchain_openai import ChatOpenAI

        from apps.agent.rag import RagRecommender
        from apps.agent.retrieval import HybridRetriever, QueryAnalyzer
        from apps.eval.embeddings import SemanticSearch

        model = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.environ["OPEN_AI_KEY"], temperature=0,
        )
        retriever = HybridRetriever(store, SemanticSearch(graph_name=graph_name))
        agent = RagRecommender(model, retriever, QueryAnalyzer(model))
        return EvalContext(agent=agent, enricher=enricher)

    if spec.get("hybrid"):  # config 5: 하이브리드 융합 + 리랭킹(전체 provenance)
        from apps.eval.embeddings import SemanticSearch
        from apps.eval.hybrid import HybridReranker, make_openai_rerank

        agent = HybridReranker(
            store, SemanticSearch(graph_name=graph_name), make_openai_rerank()
        )
        return EvalContext(agent=agent, enricher=enricher)

    if spec.get("sql"):  # config 1: 소스 eval_items 뷰에 text-to-SQL
        from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
        from apps.eval.sql_tool import SQLTool

        sql_tool = SQLTool(
            YoungcartMySQLConnector.from_env()._connect, max_rows=20, allowed_table="eval_items"
        )
        agent = build_openai_agent(GraphTools(store), sql_tool=sql_tool, max_iterations=12)
        return EvalContext(agent=agent, enricher=enricher)

    # A/B 기준선: 현재 운영 에이전트(GraphTools + semantic). 현재 GraphTools는
    # allowed_provenances를 받지 않으므로 전체 provenance로 둔다(config4=+embeddings).
    semantic_tool = None
    if spec.get("semantic"):
        from apps.eval.embeddings import SemanticSearch  # 이슈 04

        semantic_tool = SemanticSearch(graph_name=graph_name)
    agent = build_openai_agent(GraphTools(store), semantic_tool=semantic_tool, max_iterations=12)
    return EvalContext(agent=agent, enricher=enricher)
