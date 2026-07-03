"""이슈 04 — HistorySerializer: 클라이언트 히스토리(dict) → langchain 메시지."""
from langchain_core.messages import AIMessage, HumanMessage

from apps.agent.history import history_to_messages


def test_maps_roles_in_order():
    msgs = history_to_messages([
        {"role": "user", "content": "플라스크 추천"},
        {"role": "assistant", "content": "추천: Volumetric Flask (₩12,000)"},
        {"role": "user", "content": "두 번째 거 스펙"},
    ])
    assert isinstance(msgs[0], HumanMessage) and msgs[0].content == "플라스크 추천"
    assert isinstance(msgs[1], AIMessage) and "Volumetric" in msgs[1].content
    assert isinstance(msgs[2], HumanMessage)


def test_empty_history_is_empty():
    assert history_to_messages([]) == []
    assert history_to_messages(None) == []


def test_caps_to_recent_turns():
    # turns=1 → 최근 2개 메시지(1턴)만
    hist = [{"role": "user", "content": f"q{i}"} for i in range(6)]
    msgs = history_to_messages(hist, max_turns=1)
    assert len(msgs) == 2
    assert msgs[-1].content == "q5"
