"""이슈 08 — AttributeExtractor: 분류 + 통제어휘 추출 + provenance/candidate, 그래프 영속화."""
import json
from dataclasses import asdict
from datetime import datetime, timezone

from apps.agent.llm import FakeLLM
from apps.connectors.base import ProductDocument
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.extraction.extractor import AttributeExtractor, coerce_confidence
from apps.graph.store import GraphStore


def _doc() -> ProductDocument:
    return ProductDocument(
        source_id="1548728629",
        name="투명A급 메스플라스크",
        brand="ISOLAB",
        category_path=["유리실험기구", "플라스크"],
        description_text="재질 붕규산 유리 Class A",
        images=[],
        variants=[],
        content_hash="h",
        raw={},
        fetched_at=datetime.now(timezone.utc),
    )


def test_coerce_confidence_handles_words_and_numbers():
    # 실제 LLM이 confidence를 'high'/'low' 같은 말로 주는 케이스(관측) 견고 처리
    assert coerce_confidence(0.9) == 0.9
    assert coerce_confidence("0.8") == 0.8
    assert coerce_confidence("high") == 0.9
    assert coerce_confidence("low") == 0.3
    assert coerce_confidence("weird") == 1.0


# ── 추출 단위 테스트 (DB 불필요) ──
async def test_extract_classifies_type_and_attributes():
    llm = FakeLLM(json.dumps({
        "product_type": "glassware_consumable",
        "attributes": [
            {"name": "material", "value": "glass_borosilicate", "confidence": 0.9},
            {"name": "grade", "value": "class_A", "confidence": 0.95},
        ],
    }))
    result = await AttributeExtractor(llm).extract(_doc())

    assert result.product_type == "glassware_consumable"
    material = next(a for a in result.attributes if a.name == "material")
    assert material.provenance == "llm_text"
    assert material.confidence == 0.9
    assert material.is_candidate is False


async def test_unknown_attribute_marked_candidate():
    llm = FakeLLM(json.dumps({
        "product_type": "glassware_consumable",
        "attributes": [{"name": "sparkliness", "value": "high"}],
    }))
    result = await AttributeExtractor(llm).extract(_doc())
    assert result.attributes[0].is_candidate is True
    assert result.attributes[0].confidence == 1.0  # 기본값


async def test_provenance_override_for_ocr_reuse():
    llm = FakeLLM(json.dumps({
        "product_type": "electronic_instrument",
        "attributes": [{"name": "measurement_range", "value": "1-1000 mPa·s"}],
    }))
    result = await AttributeExtractor(llm, provenance="llm_ocr").extract(_doc())
    assert result.attributes[0].provenance == "llm_ocr"


# ── 그래프 영속화 (DB 필요) ──
async def test_attributes_persist_idempotently():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    doc = await YoungcartMySQLConnector.from_env().assemble("1548728629")
    await store.upsert_product(doc)

    llm = FakeLLM(json.dumps({
        "product_type": "glassware_consumable",
        "attributes": [
            {"name": "material", "value": "glass_borosilicate", "confidence": 0.9},
            {"name": "grade", "value": "class_A", "confidence": 0.95},
        ],
    }))
    result = await AttributeExtractor(llm).extract(doc)
    payload = [asdict(a) for a in result.attributes]

    await store.set_attributes(doc.source_id, payload)
    attrs = await store.get_attributes(doc.source_id)
    assert {a["name"] for a in attrs} == {"material", "grade"}
    material = next(a for a in attrs if a["name"] == "material")
    assert material["provenance"] == "llm_text"
    assert material["is_candidate"] is False

    # 멱등: 다시 set → 중복 없음
    await store.set_attributes(doc.source_id, payload)
    attrs2 = await store.get_attributes(doc.source_id)
    assert len(attrs2) == 2
