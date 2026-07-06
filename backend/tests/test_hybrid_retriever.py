"""ADR-0016 — HybridRetriever: 키워드 ∪ 시맨틱 합집합·중복제거·top-K + 설명 부착."""
from apps.agent.retrieval import HybridRetriever


class FakeKeyword:
    def __init__(self, kw):
        self._kw = kw

    async def keyword_search(self, query, limit=10):
        return self._kw[:limit]


class FakeSemantic:
    def __init__(self, results):
        self._r = results

    async def search(self, query, k=10):
        return self._r[:k]


class FakeDescriptions:
    def __init__(self, d=None):
        self._d = d or {}

    async def get_many(self, ids):
        return {i: self._d[i] for i in ids if i in self._d}


def _p(sid):
    return {"source_id": sid, "name": sid.upper()}


async def test_union_dedup_keyword_first():
    kw = FakeKeyword([_p("a"), _p("b")])
    sem = FakeSemantic([_p("b"), _p("c")])
    desc = FakeDescriptions({"a": "유리 비커 설명"})
    cands = await HybridRetriever(kw, sem, desc, top_k=10).retrieve(["q"], "q")

    assert [c["source_id"] for c in cands] == ["a", "b", "c"]     # 키워드 먼저, b 중복 제거, 그 뒤 c
    assert cands[0]["description"] == "유리 비커 설명"                 # 설명 부착
    assert cands[0]["name"] == "A"


async def test_top_k_truncates():
    kw = FakeKeyword([_p(str(i)) for i in range(30)])
    cands = await HybridRetriever(kw, FakeSemantic([]), FakeDescriptions(), top_k=5).retrieve(["q"], "q")
    assert len(cands) == 5


async def test_one_source_empty():
    # 키워드 0건이어도 시맨틱으로 후보 산출
    cands = await HybridRetriever(
        FakeKeyword([]), FakeSemantic([_p("x")]), FakeDescriptions(), top_k=10
    ).retrieve([], "q")
    assert [c["source_id"] for c in cands] == ["x"]
