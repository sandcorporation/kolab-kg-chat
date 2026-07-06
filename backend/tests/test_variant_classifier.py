"""이슈 09 — cosmetic vs functional 변형 판별(C: 변형 속성은 저장하지 않음)."""
import json

from apps.agent.llm import FakeLLM
from apps.connectors.base import SourceVariant
from apps.extraction.variants import VariantClassifier


async def test_cosmetic_color_variants():
    variants = [
        SourceVariant("1", "블루 (KA.33-62N)", 288750, {}),
        SourceVariant("2", "그레이 (KA.33-63N)", 288750, {}),
        SourceVariant("3", "오렌지 (KA.33-64N)", 288750, {}),
    ]
    llm = FakeLLM(json.dumps({"variants": [
        {"label": "블루 (KA.33-62N)", "attributes": []},
        {"label": "그레이 (KA.33-63N)", "attributes": []},
        {"label": "오렌지 (KA.33-64N)", "attributes": []},
    ]}))
    result = await VariantClassifier(llm).classify("electronic_instrument", variants)
    assert all(v.kind == "cosmetic" for v in result)


async def test_functional_capacity_variants_carry_attribute():
    variants = [
        SourceVariant("10", "50ml, NS 12/21", 15800, {}),
        SourceVariant("11", "500ml, NS 19/26", 32900, {}),
    ]
    llm = FakeLLM(json.dumps({"variants": [
        {"label": "50ml, NS 12/21", "attributes": [{"name": "capacity_ml", "value": 50, "confidence": 0.95}]},
        {"label": "500ml, NS 19/26", "attributes": [{"name": "capacity_ml", "value": 500, "confidence": 0.95}]},
    ]}))
    result = await VariantClassifier(llm).classify("glassware_consumable", variants)

    assert all(v.kind == "functional" for v in result)
    v50 = next(v for v in result if v.label.startswith("50ml"))
    assert any(a.name == "capacity_ml" and a.value == 50 for a in v50.attributes)


async def test_candidate_only_variant_is_cosmetic():
    variants = [SourceVariant("1", "스페셜에디션", 1000, {})]
    llm = FakeLLM(json.dumps({"variants": [
        {"label": "스페셜에디션", "attributes": [{"name": "edition", "value": "special"}]},
    ]}))
    result = await VariantClassifier(llm).classify("glassware_consumable", variants)
    # 어휘 밖 속성(후보)만 있으면 functional로 승격하지 않음
    assert result[0].kind == "cosmetic"
