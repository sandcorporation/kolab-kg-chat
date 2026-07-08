"""SuggestionGenerator — 응답 후 후속 검색어(칩)를 생성한다.

사용자가 타이핑 없이 클릭해 대화를 이어가도록, 직전 질의+추천 상품을 보고 짧은 후속
검색어를 2~3개 제안한다. gpt-4o-mini 배치 1콜. 실 LLM 없이 테스트하도록 model을 주입한다.
"""
from __future__ import annotations

import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage

SUGGEST_PROMPT = (
    "당신은 실험·연구 장비 쇼핑몰의 대화 도우미입니다. 사용자의 직전 질의와 추천된 상품을 보고, "
    "사용자가 클릭해 대화를 이어갈 만한 짧은 후속 검색어를 2~3개 제안하세요. "
    "상품을 비교·정제·확장하는 방향(예: '더 저렴한 것', '손잡이 있는 건?', '다른 브랜드'). "
    "각 항목은 한 줄로 짧게(질문·명령형). JSON 배열 한 줄로만 출력: [\"...\", \"...\"]"
)


def _parse(content: str) -> list[str]:
    """JSON 배열 우선, 실패 시 줄 단위. 빈 항목·따옴표·글머리표 정리."""
    try:
        arr = json.loads(re.search(r"\[.*\]", content, re.S).group(0))
        items = [str(x).strip() for x in arr if str(x).strip()]
        if items:
            return items
    except Exception:  # noqa: BLE001
        pass
    return [ln.strip(" -*\"'\t") for ln in content.splitlines() if ln.strip(" -*\"'\t")]


class LLMSuggester:
    def __init__(self, model, max_suggestions: int | None = None):
        self._model = model
        self._max = max_suggestions or int(os.environ.get("SUGGEST_MAX", "3"))

    async def suggest(self, query: str, product_names: list[str], history=None) -> list[str]:
        names = ", ".join(product_names[:8]) or "(추천 상품 없음)"
        resp = await self._model.ainvoke([
            SystemMessage(content=SUGGEST_PROMPT),
            HumanMessage(content=f"직전 질의: {query}\n추천 상품: {names}"),
        ])
        return _parse(getattr(resp, "content", "") or "")[:self._max]
