"""이슈 01 — HybridRetriever: 키워드 ∪ 시맨틱 합집합·중복제거·top-K + 속성 부착."""
from apps.agent.retrieval import HybridRetriever


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
    cands = await HybridRetriever(store, sem, top_k=10).retrieve("q")

    assert [c["source_id"] for c in cands] == ["a", "b", "c"]     # 키워드 먼저, b 중복 제거, 그 뒤 c
    assert cands[0]["attributes"] == [{"name": "material", "value": "glass"}]  # 속성 부착
    assert cands[0]["name"] == "A"


async def test_top_k_truncates():
    store = FakeStore([_p(str(i)) for i in range(30)])
    cands = await HybridRetriever(store, FakeSemantic([]), top_k=5).retrieve("q")
    assert len(cands) == 5


async def test_one_source_empty():
    # 키워드 0건이어도 시맨틱으로 후보 산출
    cands = await HybridRetriever(FakeStore([]), FakeSemantic([_p("x")]), top_k=10).retrieve("q")
    assert [c["source_id"] for c in cands] == ["x"]
