"""SSE 구조화 이벤트 스트림 (ADR-0007).

한 스트림에 token·recommendation·clarification·done·error를
`event: {type}\\ndata: {json}` 프레임으로 흘린다. 턴 단위 인라인 — Redis 없음.
실 LLM 토큰 스트리밍(langgraph astream_events)이 token 자리에 끼워진다.
"""
from __future__ import annotations

import json


def sse(event_type: str, data: dict) -> bytes:
    frame = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    return frame.encode("utf-8")


async def agent_event_stream(agent, enricher, query: str):
    """langgraph 에이전트 기반 SSE 스트림 (이슈 04, ADR-0011).

    token(추천 근거) → recommendation(결정적으로 부착된 카드) → done.
    products가 비면 UI는 근거(되묻기 문구)만 보여준다.
    """
    try:
        recommended: list[str] = []
        async for event in agent.astream(query):
            if event["type"] == "token":
                yield sse("token", {"content": event["content"]})
            elif event["type"] == "status":
                yield sse("status", {"label": event["label"]})
            elif event["type"] == "result":
                recommended = event["recommended_ids"]
        cards = await enricher.enrich(recommended)
        yield sse("recommendation", {"products": cards})
        yield sse("done", {})
    except Exception as exc:  # noqa: BLE001 — 스트림 내 오류는 error 이벤트로
        yield sse("error", {"message": str(exc)})
