"""SSE 구조화 이벤트 스트림 (ADR-0007).

한 스트림에 token·recommendation·clarification·done·error를
`event: {type}\\ndata: {json}` 프레임으로 흘린다. 턴 단위 인라인 — Redis 없음.
실 LLM 토큰 스트리밍(langgraph astream_events)이 token 자리에 끼워진다.
"""
from __future__ import annotations

import json

# 추천에 품절 상품이 포함될 때 근거 뒤에 붙이는 안내(실제 문의·구매 요청 기능은 없음).
_SOLDOUT_NOTICE = "\n\n해당 상품(들)은 품절되었습니다. 담당자에게 재고 문의 및 구매 요청을 할까요?"


def sse(event_type: str, data: dict) -> bytes:
    frame = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    return frame.encode("utf-8")


async def agent_event_stream(agent, enricher, query: str, history=None):
    """langgraph 에이전트 기반 SSE 스트림 (이슈 04, ADR-0011).

    token(추천 근거) → recommendation(결정적으로 부착된 카드) → done.
    products가 비면 UI는 근거(되묻기 문구)만 보여준다.
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
        if any(c.get("soldout") for c in cards):  # 품절 상품 포함 → 재고 문의 안내
            yield sse("token", {"content": _SOLDOUT_NOTICE})
        yield sse("recommendation", {"products": cards})
        yield sse("done", {})
    except Exception as exc:  # noqa: BLE001 — 스트림 내 오류는 error 이벤트로
        yield sse("error", {"message": str(exc)})
