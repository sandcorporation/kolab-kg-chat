"""SuggestionGenerator — 응답 후 후속 검색어(칩) 2~3개 생성."""
from langchain_core.messages import AIMessage

from apps.agent.suggest import LLMSuggester
from tests.fake_chat import ScriptedChatModel


async def test_suggest_returns_parsed_list():
    model = ScriptedChatModel(responses=[
        AIMessage(content='["손잡이 있는 건?", "더 저렴한 것", "냉장 보관은?"]')
    ])
    out = await LLMSuggester(model).suggest("비커 추천", ["메스플라스크", "비커"])
    assert out == ["손잡이 있는 건?", "더 저렴한 것", "냉장 보관은?"]


async def test_suggest_caps_at_max():
    model = ScriptedChatModel(responses=[AIMessage(content='["a","b","c","d","e"]')])
    out = await LLMSuggester(model, max_suggestions=3).suggest("q", [])
    assert out == ["a", "b", "c"]


async def test_suggest_falls_back_to_lines():
    model = ScriptedChatModel(responses=[AIMessage(content="- 더 저렴한 것\n- 다른 브랜드")])
    out = await LLMSuggester(model).suggest("q", [])
    assert out == ["더 저렴한 것", "다른 브랜드"]


async def test_suggest_empty_when_blank():
    model = ScriptedChatModel(responses=[AIMessage(content="")])
    assert await LLMSuggester(model).suggest("q", []) == []
