"""Agent Tools (이슈 02) — RecommendationAgent가 호출할 그래프 도구.

GraphStore 위 얇은 결정적 래퍼. 03에서 langchain 도구로 감싼다.
recommend(ids)는 에이전트의 최종 선택을 기록한다.
"""
from __future__ import annotations


class GraphTools:
    def __init__(self, store):
        self._store = store

    async def search_products(self, keyword: str, limit: int = 10) -> list[dict]:
        """상품명 키워드 검색 — 자연어 질의로 후보를 찾는 진입 도구."""
        return await self._store.search_products(keyword, limit=limit)

    async def find_products(self, conditions: list[dict]) -> list[str]:
        """속성 조건(AND)을 충족하는 상품 source_id 목록."""
        return await self._store.find_products_by_conditions(conditions)

    async def find_compatible(self, product_id: str, depth: int = 3) -> list[dict]:
        """product_id에서 COMPATIBLE_WITH 1..depth 홉 도달 상품."""
        return await self._store.find_compatible(product_id, max_depth=depth)

    async def get_attributes(self, product_id: str) -> list[dict]:
        """특정 상품의 Functional Attribute(근거 상세)."""
        return await self._store.get_attributes(product_id)
