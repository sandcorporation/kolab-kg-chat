"""RagRecommender (ADR-0017) — 에이전틱 반복 검색 읽기 컴포넌트.

QueryAnalyzer로 라우팅(팔로업이면 검색 스킵)하고, 만족스러운 결과가 나올 때까지 최대 N회
검색어를 바꿔가며 재시도한다. 만족 판정은 선택 단계를 재사용한다(`선택: 없음`=불만족 → 재검색).
선택 응답을 스트리밍하며 첫 줄 '선택:'을 엿봐 만족이면 나머지 근거를 흘리고, 불만족이면 스트림을
끊고(출력 토큰 절약) 재검색어를 생성해 재시도한다. astream/run 인터페이스는 기존과 동일.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from .context_trim import ContextTrimmer
from .history import history_to_messages


@dataclass
class AgentResult:
    rationale: str
    recommended_ids: list[str] = field(default_factory=list)


RAG_PROMPT = (
    "당신은 실험·연구 장비 쇼핑몰(kolabshop)의 상품 추천 도우미입니다. "
    "아래 후보 상품 중 사용자 요청에 맞는 것을 고르세요. "
    "첫 줄에 반드시 '선택: 번호, 번호'(맞는 게 없으면 '선택: 없음')를 쓰고, "
    "다음 줄부터 한국어로 추천 근거를 쓰세요. 스펙을 건조하게 나열하지 말고, 사용자의 용도에 "
    "이 상품이 왜 잘 맞는지 핵심 강점과 쓰임새를 사용자 관점에서 매력적으로 전달하세요. "
    "한국어 맞춤법과 띄어쓰기를 지켜 자연스럽게 쓰고, 여러 상품이면 각 상품을 한두 문장으로 "
    "구분해 간결하게 쓰세요. "
    "근거에서는 후보 번호(예: '17번', '추천 상품 18')를 절대 쓰지 말고 상품 이름으로 설명하세요 — "
    "그 번호는 내부용이라 사용자에게 혼란을 줍니다. "
    "근거는 후보의 이름·설명에 근거해야 하며 카탈로그에 없는 것을 지어내지 마세요. "
    "사용자가 특정 상품 유형을 지목하면(예: 플라스크·피펫·교반기), 후보 중 그 유형에 해당하는 "
    "상품만 고르세요. 재질·내열성 같은 속성만 겹치고 상품 유형이 다르면(예: 플라스크를 원하는데 "
    "합금·거치대·랙) 고르지 말고 '선택: 없음'으로 답하세요. "
    "상품 URL·이미지·가격은 시스템이 붙이니 만들지 마세요."
)

FOLLOWUP_PROMPT = (
    "이전 대화를 바탕으로 사용자의 후속 질문에 한국어로 간결히 답하세요. "
    "대화에 없는 상품 사실을 지어내지 마세요. 상품 URL·가격은 시스템이 관리합니다."
)

_FALLBACK = (
    "관련 상품을 찾지 못했습니다. 찾으시는 용도나 다른 키워드를 알려주시면 다시 찾아드리겠습니다."
)

_FILTER_FALLBACK = (
    "요청하신 조건(가격·스펙 등)에 맞는 상품을 찾지 못했습니다. 조건을 완화하거나 다르게 알려주시면 다시 찾아드리겠습니다."
)


def parse_selection(line: str) -> list[int]:
    """'선택: 2, 5' → [2,5]; '선택: 없음'/형식 이탈 → []."""
    m = re.search(r"선택\s*[:：]\s*(.+)", line)
    if not m or "없음" in m.group(1):
        return []
    return [int(x) for x in re.findall(r"\d+", m.group(1))]


def _fmt_desc(candidate: dict) -> str:
    return (candidate.get("description") or "").strip() or "설명 없음"


class RagRecommender:
    def __init__(self, model, retriever, analyzer, reranker=None, max_iters: int | None = None):
        self._model = model
        self._retriever = retriever
        self._analyzer = analyzer
        self._reranker = reranker  # None이면 리랭크 스킵(하위호환); 있으면 리랭커 주도(ADR-0019)
        self._max_iters = max_iters or int(os.environ.get("AGENT_MAX_ITERS", "3"))
        budget = int(os.environ.get("AGENT_TOKEN_BUDGET", "6000"))
        self._trimmer = ContextTrimmer(budget, token_counter=model)
        self._history_turns = int(os.environ.get("AGENT_HISTORY_TURNS", "5"))

    def _messages(self, query: str, history, candidates: list[dict]) -> list:
        cand_text = "\n".join(
            f"{i + 1}: {c['name']} — {_fmt_desc(c)}"
            for i, c in enumerate(candidates)
        ) or "(후보 없음)"
        user = HumanMessage(content=f"사용자 요청: {query}\n\n후보 상품:\n{cand_text}")
        msgs = [SystemMessage(content=RAG_PROMPT), *history_to_messages(history, self._history_turns), user]
        return self._trimmer.trim(msgs)

    async def astream(self, query: str, history=None):
        """라우팅 → (팔로업 답변 | 반복 검색 루프). status·token·result 이벤트를 낸다."""
        analysis = await self._analyzer.analyze(query, history)
        if analysis.followup:  # 이전 상품 참조 → 검색 스킵, 대화 맥락으로 답
            async for ev in self._answer_followup(query, history):
                yield ev
            return

        keywords, semantic = analysis.keywords, analysis.semantic
        filters = analysis.filters  # 숫자 하드 필터(루프 내내 유지 — 재정식화는 검색어만)
        n = max(1, self._max_iters)
        for i in range(n):
            last = i == n - 1
            yield {
                "type": "status",
                "label": "검색 중…" if i == 0 else f"다른 검색어로 다시 찾는 중… ({i + 1}/{n})",
            }
            retrieved = await self._retriever.retrieve(keywords, semantic, filters=filters)
            if not retrieved and filters:  # 필터-범인 감지: 필터 빼면 결과 있나?
                if await self._retriever.retrieve(keywords, semantic, filters=None):
                    yield {"type": "token", "content": _FILTER_FALLBACK}
                    yield {"type": "result", "recommended_ids": []}
                    return
            # 리랭커 주도(ADR-0019): 검색은 리콜 위주로 넓게, 리랭커가 ≥임계·top-K로 컷.
            # 통과 후보가 없으면 선택을 건너뛰고 바로 재검색(불만족과 동일 경로).
            candidates = retrieved
            if self._reranker is not None and retrieved:
                candidates = await self._reranker.rerank(query, retrieved)

            # 선택 스트림 + 첫 줄 '선택:' 엿보기(리랭크 통과 후보에 한해). 만족이거나 마지막이면
            # 근거를 흘리고, 불만족 & 잔여면 스트림을 끊어 재검색으로 넘어간다(출력 토큰 절약).
            header_done = False
            buffer = ""
            refs: list[int] = []
            emitted = False
            if candidates:
                async for chunk in self._model.astream(self._messages(query, history, candidates)):
                    content = getattr(chunk, "content", "") or ""
                    if not content:
                        continue
                    if header_done:
                        emitted = True
                        yield {"type": "token", "content": content}
                        continue
                    buffer += content
                    if "\n" in buffer:
                        header, rest = buffer.split("\n", 1)
                        refs = parse_selection(header)
                        header_done = True
                        if refs or last:  # 만족 or 마지막(모델 해명 살림) → 나머지 흘림
                            rest = rest.lstrip("\n")
                            if rest:
                                emitted = True
                                yield {"type": "token", "content": rest}
                        else:  # 불만족 & 잔여 → 중단
                            break
                if not header_done and buffer.strip():  # 개행 없이 끝남
                    if buffer.strip().startswith("선택"):
                        refs = parse_selection(buffer)
                    elif last:  # 형식 이탈이지만 마지막 → 통째로 근거
                        emitted = True
                        yield {"type": "token", "content": buffer}

            if refs:  # 만족
                recommended = [
                    candidates[j - 1]["source_id"] for j in refs if 1 <= j <= len(candidates)
                ]
                if not emitted:
                    yield {"type": "token", "content": (
                        "요청에 맞는 상품을 아래에서 확인하세요." if recommended else _FALLBACK
                    )}
                yield {"type": "result", "recommended_ids": recommended}
                return

            if last:  # 마지막인데 불만족 → 모델 해명을 이미 흘렸으면 그대로, 없으면 폴백
                if not emitted:
                    yield {"type": "token", "content": _FALLBACK}
                yield {"type": "result", "recommended_ids": []}
                return

            # 재검색어 생성(거부된 후보 학습 — 리랭크 전 검색 결과 기준) → 무진전이면 조기 종료
            prev_terms = (keywords, semantic)
            keywords, semantic = await self._analyzer.reformulate(
                query, prev_terms, [c["name"] for c in retrieved]
            )
            if (keywords, semantic) == prev_terms:
                yield {"type": "token", "content": _FALLBACK}
                yield {"type": "result", "recommended_ids": []}
                return

    async def _answer_followup(self, query, history):
        messages = self._trimmer.trim([
            SystemMessage(content=FOLLOWUP_PROMPT),
            *history_to_messages(history, self._history_turns),
            HumanMessage(content=query),
        ])
        emitted = False
        async for chunk in self._model.astream(messages):
            content = getattr(chunk, "content", "") or ""
            if content:
                emitted = True
                yield {"type": "token", "content": content}
        if not emitted:
            yield {"type": "token", "content": "이전 추천에 대해 궁금한 점을 구체적으로 물어봐 주세요."}
        yield {"type": "result", "recommended_ids": []}

    async def run(self, query: str, history=None) -> AgentResult:
        rationale: list[str] = []
        recommended: list[str] = []
        async for e in self.astream(query, history):
            if e["type"] == "token":
                rationale.append(e["content"])
            elif e["type"] == "result":
                recommended = e["recommended_ids"]
        return AgentResult(rationale="".join(rationale), recommended_ids=recommended)
