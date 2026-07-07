"""이슈 04 — SSE 스트리밍: langgraph 에이전트 기반 타입 이벤트(token/recommendation/done)."""
from django.test import AsyncClient

from apps.agent.runtime import AgentContext, set_agent_context
from apps.agent.streaming import agent_event_stream


class FakeAgent:
    """astream: (선택) status 알림 뒤 근거 토큰을 흘리고 최종 선택 id를 알린다."""

    def __init__(self, tokens, recommended, statuses=()):
        self._tokens = tokens
        self._recommended = recommended
        self._statuses = statuses

    async def astream(self, query, history=None):
        for label in self._statuses:
            yield {"type": "status", "label": label}
        for tok in self._tokens:
            yield {"type": "token", "content": tok}
        yield {"type": "result", "recommended_ids": self._recommended}


class FakeEnricher:
    def __init__(self, cards):
        self._cards = cards

    async def enrich(self, ids):
        return [c for c in self._cards if c["source_id"] in ids]


def _card(sid):
    return {"source_id": sid, "name": "메스플라스크", "url": f"https://x/{sid}",
            "image_url": None, "grounding": [{"name": "material", "value": "glass_borosilicate",
                                              "provenance": "structured"}]}


async def test_event_stream_emits_typed_events():
    agent = FakeAgent(tokens=["붕규산 ", "유리라 ", "추천합니다."], recommended=["1548728629"])
    enricher = FakeEnricher([_card("1548728629")])

    frames = b"".join([c async for c in agent_event_stream(agent, enricher, "유리 메스플라스크")])
    text = frames.decode("utf-8")

    assert "event: token" in text
    assert "붕규산" in text
    assert "event: recommendation" in text
    assert "1548728629" in text
    assert "event: done" in text


async def test_soldout_recommendation_appends_notice():
    # 추천에 품절 상품이 포함되면 안내 메시지를 붙이고, 카드도 그대로 보여준다.
    agent = FakeAgent(tokens=["추천합니다."], recommended=["s1"])
    card = _card("s1")
    card["soldout"] = True
    frames = b"".join([c async for c in agent_event_stream(agent, FakeEnricher([card]), "q")])
    text = frames.decode("utf-8")
    assert "품절" in text and "재고 문의" in text
    assert "event: recommendation" in text and "s1" in text


async def test_available_recommendation_has_no_soldout_notice():
    agent = FakeAgent(tokens=["추천합니다."], recommended=["1548728629"])
    frames = b"".join([c async for c in agent_event_stream(agent, FakeEnricher([_card("1548728629")]), "q")])
    assert "재고 문의" not in frames.decode("utf-8")


async def test_soldout_option_notice_names_the_option():
    # 일부 옵션 품절이면 안내가 그 옵션명을 명시한다(가격엔 포함됨).
    agent = FakeAgent(tokens=["추천합니다."], recommended=["p1"])
    card = _card("p1")
    card["soldout"] = False
    card["soldout_options"] = ["10L PE 핸들비이커"]
    frames = b"".join([c async for c in agent_event_stream(agent, FakeEnricher([card]), "q")])
    text = frames.decode("utf-8")
    assert "10L PE 핸들비이커" in text and "품절" in text and "재고 문의" in text


async def test_event_stream_emits_status_event():
    agent = FakeAgent(tokens=["추천합니다."], recommended=["1548728629"],
                      statuses=["상품 검색 중…"])
    frames = b"".join([c async for c in agent_event_stream(agent, FakeEnricher([]), "q")])
    text = frames.decode("utf-8")

    assert "event: status" in text
    assert "상품 검색 중…" in text


async def test_stream_error_becomes_error_event():
    class Boom:
        async def astream(self, query):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    frames = b"".join([c async for c in agent_event_stream(Boom(), FakeEnricher([]), "q")])
    assert "event: error" in frames.decode("utf-8")


async def test_chat_endpoint_streams_sse():
    set_agent_context(AgentContext(
        agent=FakeAgent(tokens=["추천합니다."], recommended=["1548728629"]),
        enricher=FakeEnricher([_card("1548728629")]),
    ))
    try:
        client = AsyncClient()
        response = await client.post(
            "/chat", data={"query": "유리 메스플라스크"}, content_type="application/json"
        )
        assert response.status_code == 200
        assert response["content-type"] == "text/event-stream"
        body = b"".join([chunk async for chunk in response.streaming_content]).decode("utf-8")
        assert "event: recommendation" in body
        assert "event: done" in body
        assert "1548728629" in body
    finally:
        set_agent_context(None)
