"""SSE 구조화 이벤트 스트림 (ADR-0007).

한 스트림에 token·recommendation·clarification·done·error를
`event: {type}\\ndata: {json}` 프레임으로 흘린다. 턴 단위 인라인 — Redis 없음.
실 LLM 토큰 스트리밍(langgraph astream_events)이 token 자리에 끼워진다.
"""
from __future__ import annotations

import json

_SOLDOUT_PROMPT = "담당자에게 구매요청을 할까요?"


def _soldout_items(cards) -> list[str]:
    """품절(상품 전체 또는 옵션 일부)인 추천 상품명 — 각각 '구매 요청' 버튼이 된다.
    실제 구매·문의 기능은 없다(UI 안내용)."""
    return [
        c.get("name") or "해당 상품"
        for c in cards
        if c.get("soldout") or c.get("soldout_options")
    ]


def sse(event_type: str, data: dict) -> bytes:
    frame = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    return frame.encode("utf-8")


async def agent_event_stream(agent, enricher, query: str, history=None, suggester=None):
    """langgraph 에이전트 기반 SSE 스트림 (이슈 04, ADR-0011).

    token(추천 근거) → recommendation(카드) → (notice: 품절 안내) → (suggestions: 후속 칩) → done.
    products가 비면 UI는 근거(되묻기 문구)만 보여준다. 품절 안내는 근거 텍스트와 섞지 않고
    별도 notice 이벤트로 흘려 UI가 구분된 박스로 보여준다.
    """
    try:
        recommended: list[str] = []
        async for event in agent.astream(query, history=history):
            if event["type"] == "token":
                yield sse("token", {"content": event["content"]})
            elif event["type"] == "status":
                yield sse("status", {"label": event["label"]})
            elif event["type"] == "result":
                recommended = event["recommended_ids"]
        cards = await enricher.enrich(recommended)
        yield sse("recommendation", {"products": cards})
        items = _soldout_items(cards)  # 품절 상품 → 상품별 구매요청 버튼 안내
        if items:
            yield sse("notice", {"prompt": _SOLDOUT_PROMPT, "items": items})
        if suggester is not None:  # 후속 검색어 칩(타이핑 없이 대화 지속)
            suggestions = await suggester.suggest(
                query, [c.get("name", "") for c in cards], history
            )
            if suggestions:
                yield sse("suggestions", {"suggestions": suggestions})
        yield sse("done", {})
    except Exception as exc:  # noqa: BLE001 — 스트림 내 오류는 error 이벤트로
        yield sse("error", {"message": str(exc)})
