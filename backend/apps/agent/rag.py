"""RagRecommender (이슈 02) — retrieve-then-read 읽기 컴포넌트.

검색은 HybridRetriever가 결정적으로 하고(현재 질의만), LLM은 후보를 읽고 적합한 것을
골라 근거를 쓴다(도구 호출·재검색 없음). 첫 줄 '선택: n, m'을 파싱해 추천 id를 포착하고
그 줄은 토큰 스트림에서 suppress한다. astream/run 인터페이스는 기존과 동일.
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
    "다음 줄부터 한국어로 간결한 추천 근거를 쓰세요. "
    "근거는 후보의 이름·속성에 근거해야 하며 카탈로그에 없는 것을 지어내지 마세요. "
    "상품 URL·이미지·가격은 시스템이 붙이니 만들지 마세요. "
    "이전 대화는 사용자가 이전 추천 상품을 가리킬 때만 참고하세요. "
    "사용자가 화제를 바꾸거나 포괄적으로 물으면(예: '어떤 상품 있어?') 이전 주제를 "
    "언급하지 말고 현재 후보로만 답하세요."
)


def parse_selection(line: str) -> list[int]:
    """'선택: 2, 5' → [2,5]; '선택: 없음'/형식 이탈 → []."""
    m = re.search(r"선택\s*[:：]\s*(.+)", line)
    if not m or "없음" in m.group(1):
        return []
    return [int(x) for x in re.findall(r"\d+", m.group(1))]


def _fmt_attrs(attrs: list[dict]) -> str:
    return ", ".join(f"{a['name']}={a['value']}" for a in attrs) or "속성 정보 없음"


class RagRecommender:
    def __init__(self, model, retriever, analyzer):
        self._model = model
        self._retriever = retriever
        self._analyzer = analyzer  # 질의 이해(한/영 키워드+시맨틱 질의)
        budget = int(os.environ.get("AGENT_TOKEN_BUDGET", "6000"))
        self._trimmer = ContextTrimmer(budget, token_counter=model)
        self._history_turns = int(os.environ.get("AGENT_HISTORY_TURNS", "5"))

    def _messages(self, query: str, history, candidates: list[dict]) -> list:
        cand_text = "\n".join(
            f"{i + 1}: {c['name']} — {_fmt_attrs(c['attributes'])}"
            for i, c in enumerate(candidates)
        ) or "(후보 없음)"
        user = HumanMessage(content=f"사용자 요청: {query}\n\n후보 상품:\n{cand_text}")
        msgs = [SystemMessage(content=RAG_PROMPT), *history_to_messages(history, self._history_turns), user]
        return self._trimmer.trim(msgs)

    async def astream(self, query: str, history=None):
        """status(검색 중) → 근거 token → result. 첫 줄 '선택:'은 suppress."""
        yield {"type": "status", "label": "검색 중…"}
        keywords, semantic_query = await self._analyzer.analyze(query)  # 질의 이해(현재 질의만)
        candidates = await self._retriever.retrieve(keywords, semantic_query)
        messages = self._messages(query, history, candidates)

        header_done = False
        buffer = ""
        refs: list[int] = []
        async for chunk in self._model.astream(messages):
            content = getattr(chunk, "content", "") or ""
            if not content:
                continue
            if header_done:
                yield {"type": "token", "content": content}
                continue
            buffer += content
            if "\n" in buffer:
                header, rest = buffer.split("\n", 1)
                refs = parse_selection(header)
                header_done = True
                rest = rest.lstrip("\n")
                if rest:
                    yield {"type": "token", "content": rest}
        if not header_done:  # 개행 없이 끝남
            if buffer.strip().startswith("선택"):
                refs = parse_selection(buffer)
            elif buffer.strip():
                yield {"type": "token", "content": buffer}  # 형식 이탈 → 전체를 근거로

        recommended = [
            candidates[i - 1]["source_id"] for i in refs if 1 <= i <= len(candidates)
        ]
        yield {"type": "result", "recommended_ids": recommended}

    async def run(self, query: str, history=None) -> AgentResult:
        rationale: list[str] = []
        recommended: list[str] = []
        async for e in self.astream(query, history):
            if e["type"] == "token":
                rationale.append(e["content"])
            elif e["type"] == "result":
                recommended = e["recommended_ids"]
        return AgentResult(rationale="".join(rationale), recommended_ids=recommended)
