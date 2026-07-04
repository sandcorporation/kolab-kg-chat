"""config5 — 하이브리드 융합 + 리랭킹 (에이전트 플레일링 제거).

키워드(이름)·의미(임베딩) 후보를 RRF로 융합해 풀을 만들고, LLM 리랭커가 질의 적합성으로
재정렬한다. 도구를 하나 고르는 에이전트 루프가 없어 실패·노이즈가 없고 절대 품질을 노린다.
"""
from __future__ import annotations

import json
import os

from apps.agent.recommendation_agent import AgentResult
from apps.agent.tools import GraphTools


def rrf(lists: list[list[str]], k0: int = 60) -> list[str]:
    """Reciprocal Rank Fusion — 여러 순위 리스트를 하나로 융합한다."""
    scores: dict[str, float] = {}
    for lst in lists:
        for rank, sid in enumerate(lst):
            scores[sid] = scores.get(sid, 0.0) + 1.0 / (k0 + rank + 1)
    return [sid for sid, _ in sorted(scores.items(), key=lambda x: -x[1])]


class HybridReranker:
    def __init__(self, store, semantic, rerank_fn, tools=None, pool_size: int = 20):
        self._store = store
        self._semantic = semantic
        self._rerank = rerank_fn
        self._tools = tools or GraphTools(store)
        self._pool = pool_size

    async def run(self, query: str) -> AgentResult:
        kw = [h["source_id"] for h in await self._tools.search_products(query, limit=15)]
        vec = [h["source_id"] for h in await self._semantic.search(query, k=15)]
        pool = rrf([kw, vec])[: self._pool]

        items = []
        for sid in pool:
            product = await self._store.get_product(sid)
            if product is None:
                continue
            attrs = await self._store.get_attributes(sid)
            specs = ", ".join(f"{a['name']}={a['value']}" for a in attrs[:6])
            items.append({"id": sid, "name": product["name"], "specs": specs})

        if not items:
            return AgentResult(rationale="적합한 상품을 찾지 못했습니다.", recommended_ids=[])
        ranked, rationale = await self._rerank(query, items)
        return AgentResult(rationale=rationale, recommended_ids=ranked[:5])


def make_openai_rerank(model: str | None = None):
    """실 리랭커 — 후보를 질의 적합성으로 재정렬하고 근거를 만든다."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPEN_AI_KEY"])
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    async def rerank(query, items):
        numbered = "\n".join(f"{i + 1}. {it['name']} [{it['specs']}]" for i, it in enumerate(items))
        prompt = (
            f'질의: "{query}"\n후보 상품:\n{numbered}\n\n'
            "질의에 가장 적합한 상품을 적합순으로 최대 5개 고르라(번호). 관련 없으면 제외. "
            "한국어로 간결한 추천 근거도 쓰라. "
            'JSON {"ranked":[번호,...],"rationale":"..."} 만 출력.'
        )
        resp = await client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        ids = [items[n - 1]["id"] for n in data.get("ranked", []) if isinstance(n, int) and 1 <= n <= len(items)]
        return ids, data.get("rationale", "")

    return rerank
