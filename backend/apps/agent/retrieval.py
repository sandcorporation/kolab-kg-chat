"""HybridRetriever (이슈 01) — RAG의 결정적 검색 딥모듈.

키워드 검색(GraphStore.search_products) ∪ 시맨틱 검색(SemanticSearch)을 각각 돌려
source_id로 합집합·중복제거하고 top-K를 남긴다. cross-encoder 재랭크는 하지 않는다
(리콜 위주 — 정밀도는 LLM 선택 단계가 담당). 각 후보에 이름 + 속성을 붙여 LLM이
적합성을 판단할 근거를 담는다. 히스토리는 쓰지 않는다(현재 질의만 → 결정적).
"""
from __future__ import annotations

import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage

ANALYZE_PROMPT = (
    "다음 사용자 요청에서 상품 검색용 핵심 키워드를 뽑아라. "
    "한국어와 영어를 각각 포함하라(카탈로그 상품명은 영어가 많다). "
    "'추천해줘'·'있어?'·'찾아줘' 같은 군더더기는 빼라. "
    "반드시 아래 JSON 한 줄만 출력하라: "
    '{"keywords": ["한글단어", "english word"], "semantic": "검색 의도를 담은 짧은 구(영어 권장)"}'
)


def parse_analysis(content: str, fallback_query: str) -> tuple[list[str], str]:
    """LLM JSON 출력 → (키워드 목록, 시맨틱 질의). 실패 시 원 질의로 폴백."""
    try:
        data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
        keywords = [str(x).strip() for x in data.get("keywords", []) if str(x).strip()]
        semantic = str(data.get("semantic", "")).strip()
        return (keywords or [fallback_query], semantic or fallback_query)
    except Exception:  # noqa: BLE001 — 파싱 실패는 원 질의로 폴백(검색 계속)
        return ([fallback_query], fallback_query)


class QueryAnalyzer:
    """질의 이해(LLM 1콜) — 원 질의를 한/영 키워드 + 시맨틱 질의로 정제한다.

    카탈로그 상품명이 영어라 한국어 원 질의가 검색을 놓치는 문제(KO/EN 미스매치)를
    에이전트 루프 없이 한 번에 보완한다.
    """

    def __init__(self, model):
        self._model = model

    async def analyze(self, query: str) -> tuple[list[str], str]:
        resp = await self._model.ainvoke(
            [SystemMessage(content=ANALYZE_PROMPT), HumanMessage(content=query)]
        )
        return parse_analysis(getattr(resp, "content", "") or "", query)


class HybridRetriever:
    def __init__(self, store, semantic, top_k: int | None = None):
        self._store = store          # GraphStore: search_products, get_attributes
        self._semantic = semantic    # SemanticSearch: search(keyword, k)
        self._k = top_k or int(os.environ.get("RAG_TOP_K", "20"))

    async def retrieve(self, keywords: list[str], semantic_query: str, k: int | None = None) -> list[dict]:
        """키워드 목록(한/영) 각각으로 키워드 검색 + 시맨틱 질의 1회 → 합집합·중복제거·top-K."""
        k = k or self._k
        hits: list[dict] = []
        for kw in keywords:  # 한·영 키워드 각각(KO/EN 미스매치 보완)
            hits.extend(await self._store.search_products(kw, limit=k))
        hits.extend(await self._semantic.search(semantic_query, k=k))

        seen: dict[str, dict] = {}
        for r in hits:  # 키워드 결과 먼저, 그다음 시맨틱
            sid = r["source_id"]
            if sid not in seen:
                seen[sid] = r
        ordered = list(seen.values())[:k]

        candidates: list[dict] = []
        for r in ordered:
            attrs = await self._store.get_attributes(r["source_id"])
            candidates.append({
                "source_id": r["source_id"],
                "name": r.get("name", ""),
                "attributes": attrs,
            })
        return candidates
