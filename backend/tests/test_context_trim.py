"""이슈 02 — ContextTrimmer: 토큰 예산 트리밍(시스템 유지 + 최근 우선)."""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from apps.agent.context_trim import ContextTrimmer


def _chars(msgs) -> int:
    return sum(len(str(m.content)) for m in msgs)


def test_under_budget_keeps_all():
    msgs = [SystemMessage("sys"), HumanMessage("안녕"), AIMessage("반가워요")]
    trimmer = ContextTrimmer(max_tokens=1000, token_counter=_chars)
    assert trimmer.trim(msgs) == msgs


def test_over_budget_keeps_system_and_most_recent():
    msgs = [
        SystemMessage("SYS"), HumanMessage("q1"), AIMessage("a1"),
        HumanMessage("q2"), AIMessage("a2"), HumanMessage("현재질의"),
    ]
    trimmer = ContextTrimmer(max_tokens=10, token_counter=_chars)
    out = trimmer.trim(msgs)

    assert out[0].content == "SYS"            # 시스템 프롬프트는 항상 유지
    assert out[-1].content == "현재질의"       # 최근 메시지 유지
    assert _chars(out) <= 10                   # 예산 내
    assert len(out) < len(msgs)                # 오래된 메시지 드롭


def test_trim_failure_is_safe_fallback():
    # 카운터가 폭발해도 원본을 반환(응답을 막지 않는다).
    def boom(_msgs):
        raise RuntimeError("counter boom")

    msgs = [SystemMessage("sys"), HumanMessage("q")]
    assert ContextTrimmer(max_tokens=5, token_counter=boom).trim(msgs) == msgs
