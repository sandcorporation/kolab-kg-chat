"""이슈 01 (ADR-0017) — QueryAnalyzer: 라우팅 + 검색어 + 재정식화."""
from langchain_core.messages import AIMessage

from apps.agent.query_analyzer import QueryAnalyzer
from tests.fake_chat import ScriptedChatModel


def _m(*contents):
    return ScriptedChatModel(responses=[AIMessage(content=c) for c in contents])


async def test_analyze_new_search_parses_terms():
    a = QueryAnalyzer(_m('{"keywords": ["플라스크", "flask"], "semantic": "borosilicate volumetric flask"}'))
    res = await a.analyze("내열 유리 플라스크 추천해줘", history=None)
    assert res.followup is False
    assert "flask" in res.keywords
    assert "내열 유리 플라스크 추천해줘" in res.keywords   # 원 질의 보존(직접 매칭 유지)
    assert "flask" in res.semantic.lower()


async def test_analyze_followup_when_history_present():
    a = QueryAnalyzer(_m('{"followup": true}'))
    res = await a.analyze(
        "그 중 첫 번째 어디 써?",
        history=[{"role": "assistant", "content": "메스플라스크를 추천합니다"}],
    )
    assert res.followup is True


async def test_analyze_no_history_never_followup():
    a = QueryAnalyzer(_m('{"followup": true}'))   # LLM이 잘못 followup이라 해도
    res = await a.analyze("첫 번째", history=None)
    assert res.followup is False                    # 히스토리 없으면 강제 새 검색
    assert res.keywords                              # 폴백 검색어 존재


async def test_analyze_parse_failure_falls_back_to_query():
    a = QueryAnalyzer(_m("이건 JSON이 아님"))
    res = await a.analyze("핀셋 있어?", history=None)
    assert res.followup is False
    assert res.keywords == ["핀셋 있어?"]            # 원 질의로 폴백(검색 계속)


async def test_analyze_extracts_numeric_filters():
    a = QueryAnalyzer(_m(
        '{"keywords":["원심분리기","centrifuge"],"semantic":"centrifuge",'
        '"filters":{"price_max":30000000,"purity_min":99,"storage_temp_min":2,"storage_temp_max":8}}'))
    res = await a.analyze("3000만원 이하 순도99% 냉장 원심분리기", history=None)
    assert res.filters["price"] == (None, 30000000.0)      # 이하 → hi
    assert res.filters["purity"] == (99.0, None)            # 이상 → lo
    assert res.filters["storage_temp"] == (2.0, 8.0)        # 범위


async def test_analyze_no_constraint_empty_filters():
    a = QueryAnalyzer(_m('{"keywords":["플라스크"],"semantic":"flask"}'))
    res = await a.analyze("플라스크 추천", history=None)
    assert res.filters == {}


async def test_reformulate_produces_new_terms():
    a = QueryAnalyzer(_m('{"keywords": ["교반기", "magnetic stirrer"], "semantic": "magnetic stirrer hotplate"}'))
    kws, sem = await a.reformulate(
        "자석 교반기 추천", (["stirrer"], "stirrer"), ["Flask carrier for stirrer"]
    )
    assert "magnetic stirrer" in kws
    assert "stirrer" in sem.lower()
