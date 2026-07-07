"""Reranker (ADR-0019) — 검색과 선택 사이 리랭크 딥모듈.

후보마다 질의 적합도 0~3을 매겨 임계 이상만 점수순 top_k로 남긴다. 리랭커가 결과 집합을
주도하고(선택 LLM은 유형 불일치 제거·근거로 강등), 검색은 리콜 위주로 넓게 뽑는다. 후보 수가
노출 상한 이하이면 자를 게 없어 LLM 콜을 생략한다(스킵). LLMReranker는 후보 전체를 1회 배치로
넣어 점수를 파싱한다(후보당 콜 아님). 교체 가능: 동일 인터페이스로 CrossEncoderReranker·
호스티드 API 드롭인.
"""
from __future__ import annotations

import os
import re

from langchain_core.messages import HumanMessage, SystemMessage

RERANK_PROMPT = (
    "당신은 실험·연구 장비 쇼핑몰의 검색 리랭커입니다. 사용자 질의에 대한 각 후보 상품의 "
    "적합도를 0~3으로 매기세요. 0=무관, 1=약함, 2=적합, 3=매우 적합. "
    "상품 유형·용도·스펙을 근거로 판단하세요. "
    "출력은 각 줄에 '번호: 점수'만 쓰세요(설명 없이). 모든 후보를 빠짐없이 채점하세요."
)


def _fmt_candidate(i: int, c: dict) -> str:
    desc = (c.get("description") or "").strip()
    return f"{i}: {c.get('name', '')}" + (f" — {desc}" if desc else "")


def _parse_scores(text: str) -> dict[int, int]:
    """'번호: 점수' 줄들을 파싱한다(형식 이탈 견고 — 매칭 안 되는 후보는 누락)."""
    out: dict[int, int] = {}
    for m in re.finditer(r"(\d+)\s*[:：]\s*(\d+)", text):
        out[int(m.group(1))] = int(m.group(2))
    return out


class LLMReranker:
    def __init__(self, model, top_k: int | None = None, min_score: int | None = None):
        self._model = model
        self._top_k = top_k if top_k is not None else int(os.environ.get("RERANK_TOP_K", "10"))
        self._min = min_score if min_score is not None else int(os.environ.get("RERANK_MIN_SCORE", "2"))

    async def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        if len(candidates) <= self._top_k:
            return candidates  # 자를 게 없음 → 스킵(콜 생략)
        cand_text = "\n".join(_fmt_candidate(i + 1, c) for i, c in enumerate(candidates))
        resp = await self._model.ainvoke([
            SystemMessage(content=RERANK_PROMPT),
            HumanMessage(content=f"질의: {query}\n\n후보:\n{cand_text}"),
        ])
        scores = _parse_scores(getattr(resp, "content", "") or "")
        ranked = sorted(
            ((c, scores.get(i + 1, 0)) for i, c in enumerate(candidates)),
            key=lambda t: t[1], reverse=True,
        )
        return [c for c, s in ranked if s >= self._min][:self._top_k]
