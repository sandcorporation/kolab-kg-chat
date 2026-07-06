"""이슈 02 (ADR-0017) — RagRecommender: 반복 검색 루프 + 팔로업 + 스트리밍."""
from langchain_core.messages import AIMessage

from apps.agent.query_analyzer import Analysis
from apps.agent.rag import RagRecommender, parse_selection
from tests.fake_chat import ScriptedChatModel


class FakeRetriever:
    def __init__(self, *cand_sets):
        self._sets = list(cand_sets) or [[]]
        self.calls: list[tuple] = []

    async def retrieve(self, keywords, semantic, raw_query=None, k=None):
        self.calls.append((keywords, semantic))
        idx = min(len(self.calls) - 1, len(self._sets) - 1)
        return self._sets[idx]


class FakeAnalyzer:
    def __init__(self, followup=False, terms=(["kw"], "sem"), reformulations=None):
        self._followup = followup
        self._terms = terms
        self._reforms = list(reformulations or [])
        self.reformulate_calls: list[tuple] = []

    async def analyze(self, query, history=None):
        return Analysis(followup=self._followup, keywords=self._terms[0], semantic=self._terms[1])

    async def reformulate(self, query, prev_terms, rejected):
        self.reformulate_calls.append((prev_terms, rejected))
        return self._reforms.pop(0) if self._reforms else prev_terms  # 기본 무진전


CANDS = [
    {"source_id": "1548728629", "name": "메스플라스크", "description": "유리 부피 측정 플라스크"},
    {"source_id": "p2", "name": "피펫", "description": ""},
]


def _rec(model, retriever, analyzer, max_iters=3):
    return RagRecommender(model, retriever, analyzer, max_iters=max_iters)


def _tokens(events):
    return "".join(e["content"] for e in events if e["type"] == "token")


def _result(events):
    return [e for e in events if e["type"] == "result"][-1]["recommended_ids"]


def test_parse_selection():
    assert parse_selection("선택: 1, 3") == [1, 3]
    assert parse_selection("선택: 없음") == []
    assert parse_selection("아무말") == []
    assert parse_selection("선택:2") == [2]


async def test_first_iteration_satisfied_no_retry():
    model = ScriptedChatModel(responses=[AIMessage(content="선택: 1\n\n메스플라스크는 붕규산 유리라 추천합니다.")])
    retr, analyzer = FakeRetriever(CANDS), FakeAnalyzer()
    events = [e async for e in _rec(model, retr, analyzer).astream("유리 플라스크")]

    assert "메스플라스크는 붕규산 유리라" in _tokens(events)
    assert "선택:" not in _tokens(events)                 # 선택 줄 suppress
    assert _result(events) == ["1548728629"]
    assert len(retr.calls) == 1                          # 재시도 없음
    assert analyzer.reformulate_calls == []


async def test_retry_then_satisfied_reformulates_with_rejected():
    model = ScriptedChatModel(responses=[
        AIMessage(content="선택: 없음\n\n못 찾음"),
        AIMessage(content="선택: 1\n\n찾았습니다."),
    ])
    other = [{"source_id": "x", "name": "교반기 액세서리", "description": ""}]
    retr = FakeRetriever(other, CANDS)                   # 1회차 other → 2회차 CANDS
    analyzer = FakeAnalyzer(reformulations=[(["magnetic stirrer"], "magnetic stirrer hotplate")])
    events = [e async for e in _rec(model, retr, analyzer).astream("자석 교반기")]

    assert len(retr.calls) == 2
    assert analyzer.reformulate_calls[0][1] == ["교반기 액세서리"]     # 거부 후보 전달
    assert _result(events) == ["1548728629"]
    assert any("다시" in e["label"] for e in events if e["type"] == "status")  # 재시도 status


async def test_exhausts_n_then_result_empty():
    model = ScriptedChatModel(responses=[
        AIMessage(content="선택: 없음\n\nA"), AIMessage(content="선택: 없음\n\nB"),
    ])
    retr = FakeRetriever(CANDS)
    analyzer = FakeAnalyzer(reformulations=[(["t2"], "s2")])   # 진전 있어 조기종료 안 함
    events = [e async for e in _rec(model, retr, analyzer, max_iters=2).astream("모호")]

    assert len(retr.calls) == 2
    assert _result(events) == []


async def test_no_progress_early_stop():
    model = ScriptedChatModel(responses=[AIMessage(content="선택: 없음\n\nA")])  # 1콜만 스크립트
    retr = FakeRetriever(CANDS)
    analyzer = FakeAnalyzer()                              # reformulate 기본 = prev(무진전)
    events = [e async for e in _rec(model, retr, analyzer, max_iters=3).astream("모호")]

    assert len(retr.calls) == 1                            # 1회차 후 무진전 → 종료
    assert _result(events) == []
    assert "찾지 못했" in _tokens(events)                   # 정직한 폴백


async def test_followup_skips_search():
    model = ScriptedChatModel(responses=[AIMessage(content="첫 번째 상품은 부피 측정에 씁니다.")])
    retr = FakeRetriever(CANDS)
    events = [e async for e in _rec(model, retr, FakeAnalyzer(followup=True)).astream(
        "그 중 첫 번째 어디 써?", history=[{"role": "assistant", "content": "메스플라스크 추천"}])]

    assert retr.calls == []                               # 검색 스킵
    assert "부피 측정에 씁니다" in _tokens(events)
    assert _result(events) == []


async def test_last_iteration_keeps_model_clarification():
    # max_iters=1, '선택: 없음' → 폴백 대신 모델 해명을 보여줌
    model = ScriptedChatModel(responses=[AIMessage(content="선택: 없음\n\n어떤 용도의 상품을 찾으시나요?")])
    events = [e async for e in _rec(model, FakeRetriever(CANDS), FakeAnalyzer(), max_iters=1).astream("모호")]

    assert "어떤 용도" in _tokens(events)
    assert _result(events) == []


async def test_malformed_output_is_safe():
    model = ScriptedChatModel(responses=[AIMessage(content="죄송하지만 잘 모르겠습니다")])
    events = [e async for e in _rec(model, FakeRetriever(CANDS), FakeAnalyzer(), max_iters=1).astream("q")]

    assert _result(events) == []
    assert "죄송" in _tokens(events)
