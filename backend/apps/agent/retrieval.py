"""HybridRetriever (ADR-0014/0016) — RAG의 결정적 검색 딥모듈.

키워드 검색(kg_embedding.name ILIKE) ∪ 시맨틱 검색(pgvector)을 현재 질의로 각각 돌려
source_id로 합집합·중복제거하고 top-K를 남긴다. cross-encoder 재랭크는 하지 않는다
(리콜 위주 — 정밀도는 LLM 선택 단계가 담당). 각 후보에 이름 + LLM 설명(kg_description)을
붙여 LLM이 적합성을 판단할 근거를 담는다. 히스토리는 쓰지 않는다(현재 질의만 → 결정적).

C(소스 하이드레이션): 검색·후보 근거는 전부 우리 DB(임베딩·설명, 인덱스)에서 나온다.
상품 사실(속성·가격·이미지)은 여기서 붙이지 않고, LLM이 고른 소수만 채팅 후반에 소스에서
하이드레이션한다(ProductEnricher). 적재 시 임베딩을 LLM 설명으로 강화해 raw 질의만으로
교차언어 검색이 되므로 질의이해 LLM은 없다(ADR-0015).
"""
from __future__ import annotations

import os

from apps.embeddings.filters import FILTER_COLUMNS


class HybridRetriever:
    def __init__(self, keyword, semantic, descriptions, top_k: int | None = None):
        self._keyword = keyword            # keyword_search(query, limit) → [{source_id, name}]
        self._semantic = semantic          # search(query, k) → [{source_id, name}]
        self._descriptions = descriptions  # get_many(ids) → {source_id: description}
        # 리랭크 전용 확대(ADR-0019): 리콜 위주로 넓게 뽑고 리랭커가 top-K로 컷.
        self._k = top_k or int(os.environ.get("RAG_TOP_K", "50"))

    async def retrieve(
        self, keywords: list[str], semantic_query: str,
        filters: dict | None = None, k: int | None = None,
    ) -> list[dict]:
        """분석된 검색어로 검색 → 합집합·중복제거·top-K + 설명 부착.

        키워드마다 keyword_search(한/영 각각, KO/EN 미스매치 보완) + 시맨틱 질의 1회.
        filters(숫자 하드 필터)가 있으면 두 검색에 함께 건다(ADR-0018).
        """
        k = k or self._k
        hits: list[dict] = []
        for kw in keywords:
            hits.extend(await self._keyword.keyword_search(kw, limit=k, filters=filters))
        hits.extend(await self._semantic.search(semantic_query, k=k, filters=filters))

        seen: dict[str, dict] = {}
        for r in hits:  # 키워드 결과 먼저, 그다음 시맨틱
            sid = r["source_id"]
            if sid not in seen:
                seen[sid] = r
        ordered = list(seen.values())[:k]

        descs = await self._descriptions.get_many([r["source_id"] for r in ordered])
        return [
            {
                "source_id": r["source_id"],
                "name": r.get("name", ""),
                "description": descs.get(r["source_id"], ""),
                # 레지스트리 값(가격·순도·분자량·보관온도)을 실어 리랭커가 숫자 판별을 하도록.
                **{col: r.get(col) for col in FILTER_COLUMNS},
            }
            for r in ordered
        ]
