"""VariantClassifier (이슈 09, CONTEXT: Matching Unit).

변형 판별을 추출의 부산물로 수행한다: 옵션 라벨에서 통제 어휘 속성이 추출되면
functional(그 Variant가 자체 Functional Attribute를 가짐), 아니면 cosmetic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from apps.extraction.extractor import ExtractedAttribute, coerce_confidence
from apps.extraction.vocabulary import attributes_for, is_controlled


@dataclass(frozen=True)
class ClassifiedVariant:
    variant_key: str
    label: str
    kind: str                       # "cosmetic" | "functional"
    attributes: list[ExtractedAttribute]


_PROMPT = """상품 유형 '{ptype}'의 옵션 라벨에서 통제 어휘 속성을 추출하라.
허용 속성: {attrs}
옵션: {labels}
출력 JSON: {{"variants": [{{"label","attributes":[{{"name","value","confidence"}}]}}]}}
JSON만 출력하라."""


class VariantClassifier:
    def __init__(self, llm):
        self._llm = llm

    def _prompt(self, product_type: str, variants) -> str:
        return _PROMPT.format(
            ptype=product_type,
            attrs=", ".join(attributes_for(product_type).keys()),
            labels=" | ".join(v.label for v in variants),
        )

    async def classify(self, product_type: str, variants) -> list[ClassifiedVariant]:
        raw = await self._llm.complete(self._prompt(product_type, variants))
        data = json.loads(raw)
        by_label = {e["label"]: e.get("attributes", []) for e in data.get("variants", [])}

        result = []
        for v in variants:
            attrs = [
                ExtractedAttribute(
                    name=a["name"],
                    value=a["value"],
                    provenance="llm_text",
                    confidence=coerce_confidence(a.get("confidence", 1.0)),
                    is_candidate=not is_controlled(product_type, a["name"]),
                )
                for a in by_label.get(v.label, [])
            ]
            # 통제 어휘 속성(비후보)이 하나라도 있으면 functional
            kind = "functional" if any(not a.is_candidate for a in attrs) else "cosmetic"
            result.append(
                ClassifiedVariant(
                    variant_key=v.variant_key, label=v.label, kind=kind, attributes=attrs
                )
            )
        return result
