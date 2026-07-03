"""AttributeExtractor (이슈 08, ADR-0001·0004).

ProductDocument → Product Type 분류 + 유형별 통제 어휘로 Functional Attribute 추출.
LLM이 자율로 분류·추출하며(사람 게이트 없음), 모든 속성에 provenance/confidence를
부착한다. 어휘 밖 속성은 후보(is_candidate)로 표시한다(성장 규칙).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from apps.extraction.vocabulary import PRODUCT_TYPES, attributes_for, is_controlled


@dataclass(frozen=True)
class ExtractedAttribute:
    name: str
    value: Any
    provenance: str        # "llm_text" | "llm_ocr" | "structured"
    confidence: float
    is_candidate: bool


@dataclass(frozen=True)
class ExtractionResult:
    product_type: str
    attributes: list[ExtractedAttribute]


def coerce_confidence(value) -> float:
    """LLM이 confidence를 숫자 대신 'high'/'low' 같은 말로 줄 때도 견고하게 변환."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return {"high": 0.9, "medium": 0.6, "med": 0.6, "low": 0.3}.get(
            str(value).strip().lower(), 1.0
        )


def _schema_hint() -> str:
    lines = []
    for ptype in PRODUCT_TYPES:
        names = ", ".join(attributes_for(ptype).keys())
        lines.append(f"- {ptype}: {names}")
    return "\n".join(lines)


_PROMPT = """다음 상품을 분류하고 통제 어휘로 Functional Attribute를 추출하라.
유형과 각 유형의 허용 속성:
{schema}
출력 JSON: {{"product_type": "...", "attributes": [{{"name","value","confidence"}}]}}
상품명: {name}
카테고리: {category}
설명: {description}
JSON만 출력하라."""


class StructuredExtractor:
    """LLM 없이 구조 필드에서 결정적 속성을 추출한다(이슈 26 A-테스트).

    실제 데이터의 구조 컬럼(브랜드 등)만으로 파이프라인을 관통 검증한다.
    material/temperature 같은 비정형 속성은 B(실제 LLM)에서 채운다.
    """

    async def extract(self, doc) -> ExtractionResult:
        attributes: list[ExtractedAttribute] = []
        if doc.brand:
            attributes.append(
                ExtractedAttribute(
                    name="brand", value=doc.brand, provenance="structured",
                    confidence=1.0, is_candidate=True,
                )
            )
        return ExtractionResult(product_type="general", attributes=attributes)


class AttributeExtractor:
    def __init__(self, llm, provenance: str = "llm_text"):
        self._llm = llm
        self._provenance = provenance

    def _build_prompt(self, doc) -> str:
        return _PROMPT.format(
            schema=_schema_hint(),
            name=doc.name,
            category=" > ".join(doc.category_path),
            description=doc.description_text,
        )

    async def extract(self, doc) -> ExtractionResult:
        raw = await self._llm.complete(self._build_prompt(doc))
        data = json.loads(raw)
        product_type = data["product_type"]
        attributes = [
            ExtractedAttribute(
                name=a["name"],
                value=a["value"],
                provenance=a.get("provenance", self._provenance),
                confidence=coerce_confidence(a.get("confidence", 1.0)),
                is_candidate=not is_controlled(product_type, a["name"]),
            )
            for a in data.get("attributes", [])
        ]
        return ExtractionResult(product_type=product_type, attributes=attributes)
