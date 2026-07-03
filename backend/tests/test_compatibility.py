"""이슈 18 — 호환 순회 (AGE 가변 깊이 다홉)."""
from apps.graph.store import GraphStore


async def _store_with_chain():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    # 의존 체인: 점도계 → 표준액 → 메스플라스크
    await store.add_compatibility("1667982841", "DLM-4")
    await store.add_compatibility("DLM-4", "1548728629")
    return store


async def test_traversal_reaches_multi_hop():
    store = await _store_with_chain()
    compatible = await store.find_compatible("1667982841", max_depth=3)
    depth = {c["source_id"]: c["depth"] for c in compatible}

    assert depth["DLM-4"] == 1           # 1홉
    assert depth["1548728629"] == 2      # 2홉(가변 깊이 체인)


async def test_traversal_respects_max_depth():
    store = await _store_with_chain()
    compatible = await store.find_compatible("1667982841", max_depth=1)
    ids = {c["source_id"] for c in compatible}

    assert ids == {"DLM-4"}              # 1홉까지만


async def test_add_compatibility_is_idempotent():
    store = await _store_with_chain()
    await store.add_compatibility("1667982841", "DLM-4")  # 재실행
    compatible = await store.find_compatible("1667982841", max_depth=1)
    assert len([c for c in compatible if c["source_id"] == "DLM-4"]) == 1
