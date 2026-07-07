"""SSE 구조화 이벤트 스트림 (ADR-0007).

한 스트림에 token·recommendation·clarification·done·error를
`event: {type}\\ndata: {json}` 프레임으로 흘린다. 턴 단위 인라인 — Redis 없음.
실 LLM 토큰 스트리밍(langgraph astream_events)이 token 자리에 끼워진다.
"""
from __future__ import annotations

import json

_SOLDOUT_SUFFIX = " 담당자에게 재고 문의 및 구매 요청을 할까요?"


def _soldout_notice(cards) -> str:
    """추천에 품절이 있으면 근거 뒤에 붙일 안내(품절 옵션명 명시). 실제 문의·구매 기능은 없음."""
    lines = []
    for c in cards:
        name = c.get("name") or "해당 상품"
        opts = c.get("soldout_options") or []
        if opts:  # 일부 옵션 품절 → 어떤 옵션인지 명시(가격엔 포함됨)
            lines.append(f"'{name}'의 다음 옵션은 품절되었습니다: {', '.join(opts)}")
        elif c.get("soldout"):  # 상품 전체 품절
            lines.append(f"'{name}'은(는) 품절되었습니다")
    return ("\n\n" + " / ".join(lines) + "." + _SOLDOUT_SUFFIX) if lines else ""


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
        notice = _soldout_notice(cards)  # 품절 상품·옵션 포함 → 재고 문의 안내
        if notice:
            yield sse("token", {"content": notice})
        yield sse("recommendation", {"products": cards})
        yield sse("done", {})
    except Exception as exc:  # noqa: BLE001 — 스트림 내 오류는 error 이벤트로
        yield sse("error", {"message": str(exc)})
