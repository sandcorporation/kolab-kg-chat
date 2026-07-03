"""이슈 13 — SyncOrchestrator 초기 전체 적재 (가짜 LLM/비전)."""
import json

from apps.agent.llm import FakeLLM
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.extraction.extractor import AttributeExtractor
from apps.extraction.images import FakeVisionClient, ImageAttributeExtractor
from apps.extraction.variants import VariantClassifier
from apps.graph.store import GraphStore
from apps.sync.orchestrator import IngestDeps, run_full_load

ALL_IDS = {"1712107033", "1548728629", "1667982841", "DLM-4"}


def _deps(store):
    return IngestDeps(
        connector=YoungcartMySQLConnector.from_env(),
        store=store,
        extractor=AttributeExtractor(FakeLLM(json.dumps({
            "product_type": "glassware_consumable",
            "attributes": [{"name": "material", "value": "glass_borosilicate", "confidence": 0.9}],
        }))),
        variant_classifier=VariantClassifier(FakeLLM(json.dumps({"variants": []}))),
        image_extractor=ImageAttributeExtractor(FakeVisionClient(json.dumps({"attributes": []}))),
    )


async def test_full_load_processes_all_products():
    store = GraphStore(graph_name="kg_test")
    await store.reset()

    count = await run_full_load(_deps(store))
    assert count == 4

    products = await store.list_products()
    assert {p["source_id"] for p in products} == ALL_IDS

    # 속성 추출이 그래프에 반영됨
    assert len(await store.get_attributes("1548728629")) >= 1


async def test_full_load_is_idempotent():
    store = GraphStore(graph_name="kg_test")
    await store.reset()

    await run_full_load(_deps(store))
    await run_full_load(_deps(store))  # 재실행

    products = await store.list_products()
    assert len(products) == 4  # 중복 없음
    assert len(await store.get_attributes("1548728629")) == 1  # 속성도 중복 없음
