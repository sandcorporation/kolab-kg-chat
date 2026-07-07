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
    assert "내열 유리 플라스크" in res.keywords   # 원 질의 핵심어 보존(군더더기 제거)
    assert "flask" in res.semantic.lower()


async def test_analyze_strips_noise_from_preserved_keyword():
    # 보존되는 원 질의의 군더더기(있어?·추천해줘)를 떼어 깨끗한 핵심어를 검색어로 남긴다.
    a = QueryAnalyzer(_m('{"keywords": ["tong", "clamp"], "semantic": "실험용 집게"}'))
    res = await a.analyze("집게 있어?", history=None)
    assert "집게" in res.keywords              # 군더더기 없는 핵심어 보존
    assert "집게 있어?" not in res.keywords     # 노이즈 원형은 넣지 않음


async def test_analyze_surfaces_ko_en_expansion():
    # 강화 프롬프트로 모델이 KO/EN·동의어를 확장하면 그 검색어들이 그대로 흐른다(리콜↑).
    a = QueryAnalyzer(_m('{"keywords": ["집게", "tong", "clamp", "forceps"], "semantic": "실험용 집게"}'))
    res = await a.analyze("집게 있어?", history=None)
    assert {"집게", "tong", "clamp", "forceps"} <= set(res.keywords)


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
    assert "핀셋" in res.keywords                    # 원 질의(군더더기 제거)로 폴백(검색 계속)


_CAPTURED: dict = {"msgs": None}


class _CaptureModel(ScriptedChatModel):
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        _CAPTURED["msgs"] = list(messages)
        return await super()._agenerate(messages, stop, run_manager, **kwargs)


async def test_analyze_respects_history_turns():
    hist = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"}, {"role": "assistant", "content": "a2"}]
    model = _CaptureModel(responses=[AIMessage(content='{"keywords":["k"],"semantic":"s"}')])
    await QueryAnalyzer(model, history_turns=1).analyze("새 질의", history=hist)
    # System(1) + 최근 1턴(2메시지) + Human(1) = 4 — 오래된 q1/a1은 제외
    assert len(_CAPTURED["msgs"]) == 4


async def test_analyze_history_turns_from_env(monkeypatch):
    monkeypatch.setenv("AGENT_HISTORY_TURNS", "2")
    a = QueryAnalyzer(_m('{"keywords":["k"],"semantic":"s"}'))
    assert a._history_turns == 2   # env가 하드코딩 대신 반영됨


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
