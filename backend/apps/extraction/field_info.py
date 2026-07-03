"""field_info 구조 스펙 → Functional Attribute (결정적, LLM 불필요).

커넥터가 Variant.raw['field_info']에 실어준 field_info 행에서 스펙 컬럼을 골라
provenance=structured 속성으로 변환한다. 원본 텍스트 그대로(정규화 없음).
"""
from __future__ import annotations

from apps.extraction.extractor import ExtractedAttribute
from apps.extraction.vocabulary import is_controlled

# field_info 컬럼 → 속성 이름 (어휘 확장분과 일치)
_FIELD_MAP = {
    "purity": "purity",
    "cas_number": "cas_number",
    "molecular_formula": "molecular_formula",
    "molecular_weight": "molecular_weight",
    "boiling_point": "boiling_point",
    "melting_point": "melting_point",
    "density": "density",
    "solubility": "solubility",
    "storage": "storage",
    "hazard_statements": "hazard_statements",
}


def field_info_attributes(
    field_info: dict, product_type: str = "reagent_chemical"
) -> list[ExtractedAttribute]:
    attributes: list[ExtractedAttribute] = []
    for column, name in _FIELD_MAP.items():
        value = field_info.get(column)
        if isinstance(value, str):
            value = value.strip()
        if not value:
            continue
        attributes.append(
            ExtractedAttribute(
                name=name,
                value=value,
                provenance="structured",
                confidence=1.0,
                is_candidate=not is_controlled(product_type, name),
            )
        )
    return attributes
