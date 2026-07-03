"""이슈 14 — delta: content-hash 게이팅 + 코얼레싱 + 변경 감지 폴러."""
import json

from apps.agent.llm import FakeLLM
from apps.connectors.base import ProductChanged
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.extraction.extractor import AttributeExtractor
from apps.extraction.images import FakeVisionClient, ImageAttributeExtractor
from apps.extraction.variants import VariantClassifier
from apps.graph.store import GraphStore
from apps.sync.orchestrator import IngestDeps, coalesce, process_delta
from apps.sync.poller import DiffPoller

ALL_IDS = {"1712107033", "1548728629", "1667982841", "DLM-4"}


class CountingLLM:
    def __init__(self, response: str):
        self._inner = FakeLLM(response)
        self.calls = 0

    async def complete(self, prompt: str) -> str:
        self.calls += 1
        return await self._inner.complete(prompt)


async def _fresh_deps():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    extractor_llm = CountingLLM(json.dumps({
        "product_type": "glassware_consumable",
        "attributes": [{"name": "material", "value": "glass_borosilicate", "confidence": 0.9}],
    }))
    deps = IngestDeps(
        connector=YoungcartMySQLConnector.from_env(),
        store=store,
        extractor=AttributeExtractor(extractor_llm),
        variant_classifier=VariantClassifier(FakeLLM(json.dumps({"variants": []}))),
        image_extractor=ImageAttributeExtractor(FakeVisionClient(json.dumps({"attributes": []}))),
    )
    return deps, extractor_llm


async def test_delta_gates_unchanged_by_content_hash():
    deps, extractor_llm = await _fresh_deps()

    first = await process_delta(deps, "1548728629")
    assert first in ("created", "updated")
    assert extractor_llm.calls == 1

    second = await process_delta(deps, "1548728629")  # 소스 그대로 → 게이팅
    assert second == "unchanged"
    assert extractor_llm.calls == 1  # 재추출 생략


async def test_delta_deletes_missing_source():
    deps, _ = await _fresh_deps()
    await process_delta(deps, "DLM-4")
    assert await deps.store.get_product("DLM-4") is not None

    assert await process_delta(deps, "does-not-exist") == "deleted"
    assert await deps.store.get_product("does-not-exist") is None


def test_coalesce_dedups_burst():
    changes = [
        ProductChanged("a", "updated"),
        ProductChanged("a", "updated"),
        ProductChanged("b", "created"),
    ]
    assert set(coalesce(changes)) == {"a", "b"}


async def test_poller_detects_created_then_stable():
    poller = DiffPoller(YoungcartMySQLConnector.from_env())
    changes, snap = await poller.poll({})
    assert {c.source_id for c in changes} == ALL_IDS
    assert all(c.op == "created" for c in changes)

    changes2, _ = await poller.poll(snap)
    assert changes2 == []  # 변화 없음


async def test_poller_detects_updated_and_deleted():
    poller = DiffPoller(YoungcartMySQLConnector.from_env())
    _, snap = await poller.poll({})

    fake_prev = dict(snap)
    fake_prev["1548728629"] = "STALE_HASH"   # 변경된 것처럼
    fake_prev["ghost"] = "x"                  # 사라진 것처럼
    changes, _ = await poller.poll(fake_prev)

    ops = {c.source_id: c.op for c in changes}
    assert ops.get("1548728629") == "updated"
    assert ops.get("ghost") == "deleted"
