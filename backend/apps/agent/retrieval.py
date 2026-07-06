"""HybridRetriever (이슈 01, ADR-0014) — RAG의 결정적 검색 딥모듈.

키워드 검색(GraphStore.search_products) ∪ 시맨틱 검색(SemanticSearch)을 현재 질의로 각각
돌려 source_id로 합집합·중복제거하고 top-K를 남긴다. cross-encoder 재랭크는 하지 않는다
(리콜 위주 — 정밀도는 LLM 선택 단계가 담당). 각 후보에 이름 + 속성을 붙여 LLM이 적합성을
판단할 근거를 담는다. 히스토리는 쓰지 않는다(현재 질의만 → 결정적).

질의이해(KO/EN 번역) LLM은 제거됐다(ADR-0014 확장, Route C): 상품 임베딩을 적재 시 LLM
설명으로 강화해, raw 질의만으로 교차언어 검색이 되도록 인덱스가 지능을 가진다.
"""
from __future__ import annotations

import os


class HybridRetriever:
    def __init__(self, store, semantic, top_k: int | None = None):
        self._store = store          # GraphStore: search_products, get_attributes
        self._semantic = semantic    # SemanticSearch: search(keyword, k)
        self._k = top_k or int(os.environ.get("RAG_TOP_K", "20"))

    async def retrieve(self, query: str, k: int | None = None) -> list[dict]:
        """현재 질의로 키워드 ∪ 시맨틱 검색 → 합집합·중복제거·top-K + 속성 부착."""
        k = k or self._k
        keyword = await self._store.search_products(query, limit=k)
        semantic = await self._semantic.search(query, k=k)

        seen: dict[str, dict] = {}
        for r in [*keyword, *semantic]:  # 키워드 먼저, 그다음 시맨틱
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
