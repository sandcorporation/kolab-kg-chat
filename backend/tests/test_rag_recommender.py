"""이슈 02 — RagRecommender: 후보 읽기 → 선택 + 근거(도구 없음)."""
from langchain_core.messages import AIMessage

from apps.agent.rag import RagRecommender, parse_selection
from tests.fake_chat import ScriptedChatModel


class FakeRetriever:
    def __init__(self, cands):
        self._c = cands
        self.calls: list[str] = []

    async def retrieve(self, query, k=None):
        self.calls.append(query)
        return self._c


CANDS = [
    {"source_id": "1548728629", "name": "메스플라스크", "attributes": [{"name": "material", "value": "glass"}]},
    {"source_id": "p2", "name": "피펫", "attributes": []},
]


def test_parse_selection():
    assert parse_selection("선택: 1, 3") == [1, 3]
    assert parse_selection("선택: 없음") == []
    assert parse_selection("아무말") == []
    assert parse_selection("선택:2") == [2]


async def test_astream_selects_and_streams_rationale():
    model = ScriptedChatModel(responses=[AIMessage(content="선택: 1\n\n메스플라스크는 붕규산 유리라 추천합니다.")])
    events = [e async for e in RagRecommender(model, FakeRetriever(CANDS)).astream("유리 플라스크")]

    assert events[0]["type"] == "status" and "검색" in events[0]["label"]
    tokens = "".join(e["content"] for e in events if e["type"] == "token")
    assert "메스플라스크는 붕규산 유리라" in tokens
    assert "선택:" not in tokens                                   # 선택 줄 suppress
    result = [e for e in events if e["type"] == "result"][-1]
    assert result["recommended_ids"] == ["1548728629"]            # 번호 1 → source_id


async def test_selection_none_gives_empty_and_clarifies():
    model = ScriptedChatModel(responses=[AIMessage(content="선택: 없음\n\n어떤 용도의 상품을 찾으시나요?")])
    events = [e async for e in RagRecommender(model, FakeRetriever(CANDS)).astream("모호")]

    result = [e for e in events if e["type"] == "result"][-1]
    assert result["recommended_ids"] == []
    assert "어떤 용도" in "".join(e["content"] for e in events if e["type"] == "token")


async def test_retrieval_uses_current_query_only():
    # 검색은 현재 질의로만 구동된다(히스토리 무관) — 앵커링 버그 근본 해소
    retriever = FakeRetriever(CANDS)
    model = ScriptedChatModel(responses=[AIMessage(content="선택: 없음\n\n네.")])
    _ = [e async for e in RagRecommender(model, retriever).astream(
        "어떤 상품 있어?",
        history=[{"role": "user", "content": "핀셋있어?"},
                 {"role": "assistant", "content": "핀셋 못 찾음"}],
    )]
    assert retriever.calls == ["어떤 상품 있어?"]  # 히스토리 아닌 현재 질의만 검색


async def test_empty_selection_without_rationale_still_speaks():
    # '선택: 없음'만 쓰고 근거를 안 남겨도 침묵하지 않는다(빈 말풍선 방지)
    model = ScriptedChatModel(responses=[AIMessage(content="선택: 없음")])
    events = [e async for e in RagRecommender(model, FakeRetriever(CANDS)).astream("모호")]
    tokens = "".join(e["content"] for e in events if e["type"] == "token")
    assert tokens.strip()                                             # 안내 메시지 방출
    assert [e for e in events if e["type"] == "result"][-1]["recommended_ids"] == []


async def test_selection_without_rationale_still_speaks():
    # 추천은 있으나 근거를 안 쓴 경우에도 안내를 방출한다
    model = ScriptedChatModel(responses=[AIMessage(content="선택: 1")])
    events = [e async for e in RagRecommender(model, FakeRetriever(CANDS)).astream("유리")]
    assert "".join(e["content"] for e in events if e["type"] == "token").strip()
    assert [e for e in events if e["type"] == "result"][-1]["recommended_ids"] == ["1548728629"]


async def test_malformed_output_is_safe():
    # 선택 줄 형식을 안 지켜도 근거는 보이고 추천은 비운다
    model = ScriptedChatModel(responses=[AIMessage(content="죄송하지만 잘 모르겠습니다")])
    events = [e async for e in RagRecommender(model, FakeRetriever(CANDS)).astream("q")]
    result = [e for e in events if e["type"] == "result"][-1]
    assert result["recommended_ids"] == []
    assert "죄송" in "".join(e["content"] for e in events if e["type"] == "token")
