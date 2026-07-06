"""QueryAnalyzer (ADR-0017) — 질의 이해 + 팔로업 라우팅 + 재검색어 생성.

원 질의에서 한/영 키워드 + 시맨틱 질의를 뽑아 KO/EN 미스매치를 보완한다(ADR-0015에서 비용
위해 제거했던 것을 품질 위해 복구). 반복 검색 루프가 쓰도록 두 능력을 더한다:
- analyze(query, history): 팔로업(이전 상품 참조)인지 라우팅 + 새 검색이면 초기 검색어
- reformulate(query, prev_terms, rejected): 거부된 후보를 학습해 직전과 다른 검색어

파싱 실패·형식 이탈은 원 질의로 폴백해 검색을 계속한다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from .history import history_to_messages

ANALYZE_PROMPT = (
    "사용자 요청과 이전 대화를 보고 상품 검색 계획을 세워라. "
    "요청이 이전에 보여준 상품을 가리키는 후속 질문이면(예: '그 중 첫 번째', '방금 그거', "
    "'이 제품 어디 써') 반드시 {\"followup\": true} 만 출력하라. "
    "그 외 새로운 상품 탐색이면 검색용 핵심 키워드를 뽑아라(한국어·영어 각각, 카탈로그 상품명은 "
    "영어가 많다). '추천해줘'·'있어?'·'찾아줘' 같은 군더더기는 빼라. "
    "이전 대화가 없으면 절대 followup이 아니다. "
    "원 질의의 핵심 명사는 그대로 keywords에 남기고 번역·동의어를 덧붙여라(직접 매칭 보존). "
    '출력 JSON 한 줄: {"keywords": ["한글단어", "english word"], "semantic": "검색 의도를 담은 짧은 구(영어 권장)"}'
)

REFORMULATE_PROMPT = (
    "직전 검색어로 찾은 후보가 사용자 요청에 맞지 않았다. 다른 각도의 검색어를 제시하라. "
    "직전 검색어와 겹치지 않게 동의어·상위/하위 개념·영문 변형을 시도하라. "
    '출력 JSON 한 줄: {"keywords": ["한글단어", "english word"], "semantic": "짧은 구(영어 권장)"}'
)


@dataclass
class Analysis:
    followup: bool
    keywords: list[str] = field(default_factory=list)
    semantic: str = ""


def _parse_terms(content: str, fallback_query: str) -> tuple[list[str], str]:
    """LLM JSON → (키워드 목록, 시맨틱 질의). 실패 시 원 질의로 폴백."""
    try:
        data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
        keywords = [str(x).strip() for x in data.get("keywords", []) if str(x).strip()]
        semantic = str(data.get("semantic", "")).strip()
        return (keywords or [fallback_query], semantic or fallback_query)
    except Exception:  # noqa: BLE001 — 파싱 실패는 원 질의로 폴백(검색 계속)
        return ([fallback_query], fallback_query)


def _is_followup(content: str) -> bool:
    try:
        data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
        return bool(data.get("followup"))
    except Exception:  # noqa: BLE001
        return False


class QueryAnalyzer:
    def __init__(self, model):
        self._model = model
        self._history_turns = 5

    async def analyze(self, query: str, history=None) -> Analysis:
        """라우팅 + 초기 검색어. 히스토리 없으면 절대 followup 아님(강제 새 검색)."""
        messages = [
            SystemMessage(content=ANALYZE_PROMPT),
            *history_to_messages(history, self._history_turns),
            HumanMessage(content=query),
        ]
        content = await self._invoke(messages)
        if history and _is_followup(content):
            return Analysis(followup=True)
        keywords, semantic = _parse_terms(content, query)
        # keyword 드리프트 완화: 원 질의를 검색어에 항상 보존(직접 매칭 유지 + 확장 추가).
        if query not in keywords:
            keywords = [query, *keywords]
        return Analysis(followup=False, keywords=keywords, semantic=semantic)

    async def reformulate(
        self, query: str, prev_terms: tuple[list[str], str], rejected_names: list[str]
    ) -> tuple[list[str], str]:
        """거부된 후보를 학습해 직전과 다른 검색어를 생성."""
        prev_kw, prev_sem = prev_terms
        human = (
            f"사용자 요청: {query}\n"
            f"직전 검색어: {', '.join(prev_kw)} / {prev_sem}\n"
            f"맞지 않은 후보: {', '.join(rejected_names[:15]) or '(없음)'}"
        )
        content = await self._invoke([
            SystemMessage(content=REFORMULATE_PROMPT), HumanMessage(content=human)
        ])
        return _parse_terms(content, query)

    async def _invoke(self, messages) -> str:
        try:
            resp = await self._model.ainvoke(messages)
            return getattr(resp, "content", "") or ""
        except Exception:  # noqa: BLE001 — 분석 실패는 폴백으로 흡수
            return ""
