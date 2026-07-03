"""이슈 04 — 비전 수집 트레이서: 이미지 속성이 llm_ocr로 병합, 비전 실패 시 건너뜀."""
import json

from apps.agent.llm import FakeLLM
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.extraction.extractor import AttributeExtractor
from apps.extraction.images import FakeVisionClient, ImageAttributeExtractor
from apps.extraction.variants import VariantClassifier
from apps.graph.store import GraphStore
from apps.sync.orchestrator import IngestDeps, process_product


def _deps(store, vision):
    return IngestDeps(
        connector=YoungcartMySQLConnector.from_env(),
        store=store,
        extractor=AttributeExtractor(FakeLLM(json.dumps({
            "product_type": "glassware_consumable",
            "attributes": [{"name": "grade", "value": "class_A", "confidence": 0.9}],
        }))),
        variant_classifier=VariantClassifier(FakeLLM(json.dumps({"variants": []}))),
        image_extractor=ImageAttributeExtractor(vision),
    )


async def _fresh():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    return store


async def test_image_attributes_merge_as_llm_ocr():
    store = await _fresh()
    vision = FakeVisionClient(json.dumps({
        "attributes": [{"name": "material", "value": "glass_borosilicate", "confidence": 0.7}],
    }))
    await process_product(_deps(store, vision), "1548728629")  # 플라스크: 이미지 보유

    provenance = {a["name"]: a["provenance"] for a in await store.get_attributes("1548728629")}
    assert provenance.get("material") == "llm_ocr"   # 이미지 유래
    assert provenance.get("grade") == "llm_text"     # 텍스트 유래


async def test_vision_failure_skips_but_product_continues():
    store = await _fresh()

    class BoomVision:
        model_version = "boom"

        async def extract(self, *args, **kwargs):
            raise RuntimeError("vision down")

    ok = await process_product(_deps(store, BoomVision()), "1548728629")
    assert ok is True
    names = {a["name"] for a in await store.get_attributes("1548728629")}
    assert "grade" in names        # 텍스트 속성은 유지
    assert "material" not in names  # 비전 실패 → 이미지 속성 없음(크래시 없음)
