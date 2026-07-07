"""QueryAnalyzer (ADR-0017) — 질의 이해 + 팔로업 라우팅 + 재검색어 생성.

원 질의에서 한/영 키워드 + 시맨틱 질의를 뽑아 KO/EN 미스매치를 보완한다(ADR-0015에서 비용
위해 제거했던 것을 품질 위해 복구). 반복 검색 루프가 쓰도록 두 능력을 더한다:
- analyze(query, history): 팔로업(이전 상품 참조)인지 라우팅 + 새 검색이면 초기 검색어
- reformulate(query, prev_terms, rejected): 거부된 후보를 학습해 직전과 다른 검색어

파싱 실패·형식 이탈은 원 질의로 폴백해 검색을 계속한다.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from apps.embeddings.filters import FILTER_SPEC

from .history import history_to_messages

ANALYZE_PROMPT = (
    "사용자 요청과 이전 대화를 보고 상품 검색 계획을 세워라. "
    "요청이 이전에 보여준 상품을 가리키는 후속 질문이면(예: '그 중 첫 번째', '방금 그거', "
    "'이 제품 어디 써') 반드시 {\"followup\": true} 만 출력하라. "
    "그 외 새로운 상품 탐색이면 검색용 핵심 키워드를 뽑아라. 반드시 한국어와 영어를 모두 포함하고"
    "(카탈로그 상품명은 영어가 많다), 짧거나 모호한 질의일수록 동의어·상위/하위 유형까지 넉넉히 "
    "확장하라(예: '집게'→집게, tong, clamp, forceps, tweezers, retriever). 뒤에서 리랭커가 "
    "부적합을 걸러내므로 넓게 뽑는 게 이득이다. '추천해줘'·'있어?'·'찾아줘' 같은 군더더기와 말미의 "
    "조사·의문은 빼라. 이전 대화가 없으면 절대 followup이 아니다. "
    "원 질의의 핵심 명사는 그대로 keywords에 남기고 번역·동의어를 덧붙여라(직접 매칭 보존). "
    "숫자 제약이 있으면 filters에 넣어라(제약 있을 때만): price(원), purity(%), molecular_weight, "
    "storage_temp(℃; 냉장=2~8·냉동≤-20·실온=15~25). 이하는 {필드}_max, 이상은 {필드}_min, 범위는 둘 다. "
    "예: '3000만원 이하'→price_max:30000000, '순도 99% 이상'→purity_min:99, '냉장/2~8도'→"
    "storage_temp_min:2,storage_temp_max:8. 브랜드·재질 등은 filters가 아니라 keywords/semantic으로. "
    '출력 JSON 한 줄: {"keywords": ["한글단어", "english word"], "semantic": "검색 의도를 담은 짧은 구", "filters": {}}'
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
    filters: dict = field(default_factory=dict)  # {name:(lo,hi)} 숫자 하드 필터(ADR-0018)


def _parse_filters(content: str) -> dict:
    """LLM JSON의 filters({필드}_min/_max) → {name:(lo,hi)}. 실패·없음 → {}."""
    try:
        data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
        raw = data.get("filters") or {}
        out: dict = {}
        for f in FILTER_SPEC:
            lo, hi = raw.get(f"{f.name}_min"), raw.get(f"{f.name}_max")
            if lo is not None or hi is not None:
                out[f.name] = (
                    float(lo) if lo is not None else None,
                    float(hi) if hi is not None else None,
                )
        return out
    except Exception:  # noqa: BLE001
        return {}


def _parse_terms(content: str, fallback_query: str) -> tuple[list[str], str]:
    """LLM JSON → (키워드 목록, 시맨틱 질의). 실패 시 원 질의로 폴백."""
    try:
        data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
        keywords = [str(x).strip() for x in data.get("keywords", []) if str(x).strip()]
        semantic = str(data.get("semantic", "")).strip()
        return (keywords or [fallback_query], semantic or fallback_query)
    except Exception:  # noqa: BLE001 — 파싱 실패는 원 질의로 폴백(검색 계속)
        return ([fallback_query], fallback_query)


_NOISE_WORDS = (
    "있어", "있나요", "있니", "있을까", "없어", "없나요", "추천해줘", "추천해", "추천",
    "찾아줘", "찾아", "알려줘", "보여줘", "주세요", "해줘", "줘",
)
_NOISE_RE = re.compile(r"[\s,]*(?:" + "|".join(_NOISE_WORDS) + r")[\s?!.]*$")


def _strip_query_noise(query: str) -> str:
    """검색어로 보존할 원 질의에서 말미의 군더더기·의문을 떼어 깨끗한 핵심어만 남긴다.

    '집게 있어?'→'집게', '내열 유리 플라스크 추천해줘'→'내열 유리 플라스크'. 여러 개 붙어도
    반복 제거. 다 떼어 비면 원 질의를 그대로 둔다(검색 계속).
    """
    q = (query or "").strip()
    prev = None
    while prev != q and q:
        prev = q
        q = _NOISE_RE.sub("", q).strip().rstrip("?!.").strip()
    return q or query.strip()


def _is_followup(content: str) -> bool:
    try:
        data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
        return bool(data.get("followup"))
    except Exception:  # noqa: BLE001
        return False


class QueryAnalyzer:
    def __init__(self, model, history_turns: int | None = None):
        self._model = model
        # 유지할 최근 대화 턴 수 — RagRecommender와 같은 단일 env(AGENT_HISTORY_TURNS)로 제어.
        self._history_turns = history_turns or int(os.environ.get("AGENT_HISTORY_TURNS", "5"))

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
        # keyword 드리프트 완화: 원 질의의 핵심어(군더더기 제거)를 항상 보존(직접 매칭 유지 + 확장 추가).
        core = _strip_query_noise(query)
        if core not in keywords:
            keywords = [core, *keywords]
        return Analysis(
            followup=False, keywords=keywords, semantic=semantic,
            filters=_parse_filters(content),
        )

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
