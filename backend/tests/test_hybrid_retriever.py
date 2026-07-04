"""이슈 01 — HybridRetriever: 키워드 ∪ 시맨틱 합집합·중복제거·top-K + 속성 부착."""
from langchain_core.messages import AIMessage

from apps.agent.retrieval import HybridRetriever, QueryAnalyzer, parse_analysis
from tests.fake_chat import ScriptedChatModel


class FakeStore:
    def __init__(self, kw, attrs=None):
        self._kw = kw
        self._attrs = attrs or {}

    async def search_products(self, keyword, limit=10):
        return self._kw[:limit]

    async def get_attributes(self, source_id):
        return self._attrs.get(source_id, [])


class FakeSemantic:
    def __init__(self, results):
        self._r = results

    async def search(self, keyword, k=10):
        return self._r[:k]


def _p(sid):
    return {"source_id": sid, "name": sid.upper()}


async def test_union_dedup_keyword_first():
    store = FakeStore([_p("a"), _p("b")], {"a": [{"name": "material", "value": "glass"}]})
    sem = FakeSemantic([_p("b"), _p("c")])
    cands = await HybridRetriever(store, sem, top_k=10).retrieve(["k"], "s")

    assert [c["source_id"] for c in cands] == ["a", "b", "c"]     # 키워드 먼저, b 중복 제거, 그 뒤 c
    assert cands[0]["attributes"] == [{"name": "material", "value": "glass"}]  # 속성 부착
    assert cands[0]["name"] == "A"


async def test_top_k_truncates():
    store = FakeStore([_p(str(i)) for i in range(30)])
    cands = await HybridRetriever(store, FakeSemantic([]), top_k=5).retrieve(["k"], "s")
    assert len(cands) == 5


async def test_one_source_empty():
    # 키워드 0건이어도 시맨틱으로 후보 산출
    cands = await HybridRetriever(FakeStore([]), FakeSemantic([_p("x")]), top_k=10).retrieve(["k"], "s")
    assert [c["source_id"] for c in cands] == ["x"]


async def test_multiple_keywords_unioned():
    # 한·영 키워드 각각 검색되어 합쳐진다
    class MultiStore(FakeStore):
        async def search_products(self, keyword, limit=10):
            return {"플라스크": [_p("a")], "flask": [_p("b")]}.get(keyword, [])
    cands = await HybridRetriever(MultiStore([]), FakeSemantic([]), top_k=10).retrieve(
        ["플라스크", "flask"], "flask"
    )
    assert {c["source_id"] for c in cands} == {"a", "b"}


def test_parse_analysis_ok():
    kw, sem = parse_analysis('{"keywords": ["플라스크", "flask"], "semantic": "flask"}', "raw")
    assert kw == ["플라스크", "flask"] and sem == "flask"


def test_parse_analysis_fallback_on_bad_json():
    kw, sem = parse_analysis("죄송 JSON 아님", "피펫")
    assert kw == ["피펫"] and sem == "피펫"


async def test_query_analyzer_extracts_ko_en():
    model = ScriptedChatModel(responses=[
        AIMessage(content='{"keywords": ["플라스크", "flask"], "semantic": "flask"}')
    ])
    kw, sem = await QueryAnalyzer(model).analyze("플라스크 추천해줘")
    assert "flask" in kw and "플라스크" in kw and sem == "flask"
