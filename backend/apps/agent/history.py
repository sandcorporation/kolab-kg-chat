"""HistorySerializer (이슈 04) — 클라이언트가 보낸 대화 히스토리를 메시지로 변환.

무상태 멀티턴: 서버는 세션을 저장하지 않고, 프론트가 최근 N턴을 요청에 담아 보낸다.
role: user → HumanMessage, 그 외(assistant/bot) → AIMessage. max_turns로 최근 턴만 남긴다.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage


def history_to_messages(history, max_turns: int | None = None) -> list:
    if not history:
        return []
    items = list(history)
    if max_turns is not None:
        items = items[-(max_turns * 2):]  # 1턴 = user+assistant 2메시지
    out = []
    for h in items:
        role = h.get("role", "")
        content = h.get("content", "") or ""
        out.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
    return out
