"""유형별 통제 어휘 (이슈 05, ADR-0001).

AttributeExtractor(이슈 08)가 소비하는 기계용 정의. 사람용 사양은
`docs/controlled-vocabulary.md` 참조.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AttrKind(str, Enum):
    NUMERIC_RANGE = "numeric_range"
    ENUM = "enum"
    BOOLEAN = "boolean"
    SCALAR = "scalar"


@dataclass(frozen=True)
class AttributeDef:
    name: str
    kind: AttrKind
    unit: str | None = None
    allowed: tuple[str, ...] = ()      # enum 허용값
    multi: bool = False                # enum 다중값 여부
    description: str = ""


def _defs(*defs: AttributeDef) -> dict[str, AttributeDef]:
    return {d.name: d for d in defs}


VOCABULARY: dict[str, dict[str, AttributeDef]] = {
    "glassware_consumable": _defs(
        AttributeDef("material", AttrKind.ENUM, allowed=(
            "glass_borosilicate", "glass_soda_lime", "PP", "PTFE", "PE",
            "PMP", "PC", "stainless_steel", "silicone",
        )),
        AttributeDef("temperature_min", AttrKind.NUMERIC_RANGE, unit="℃"),
        AttributeDef("temperature_max", AttrKind.NUMERIC_RANGE, unit="℃"),
        AttributeDef("chemical_resistance", AttrKind.ENUM,
                     allowed=("acid", "base", "solvent", "oxidizer"), multi=True),
        AttributeDef("sterility", AttrKind.ENUM, allowed=(
            "non_sterile", "sterile", "rnase_free", "dnase_free",
            "pyrogen_free", "cell_culture_grade",
        )),
        AttributeDef("capacity_ml", AttrKind.NUMERIC_RANGE, unit="mL"),
        AttributeDef("grade", AttrKind.ENUM, allowed=("class_A", "class_B")),
        AttributeDef("light_protection", AttrKind.BOOLEAN, description="차광"),
        AttributeDef("autoclavable", AttrKind.BOOLEAN),
    ),
    "electronic_instrument": _defs(
        AttributeDef("measurement_range", AttrKind.SCALAR),
        AttributeDef("accuracy", AttrKind.SCALAR),
        AttributeDef("power_source", AttrKind.ENUM,
                     allowed=("rechargeable", "ac_adapter", "battery", "usb")),
        AttributeDef("interface", AttrKind.ENUM,
                     allowed=("none", "rs232", "usb", "bluetooth", "ethernet", "wifi")),
        AttributeDef("channels", AttrKind.NUMERIC_RANGE, unit="count"),
        AttributeDef("display", AttrKind.ENUM, allowed=("none", "lcd", "led", "touch")),
        AttributeDef("compatible_accessories", AttrKind.SCALAR),
    ),
    "reagent_chemical": _defs(
        AttributeDef("purity_percent", AttrKind.NUMERIC_RANGE, unit="%"),
        AttributeDef("cas_number", AttrKind.SCALAR),
        AttributeDef("concentration", AttrKind.SCALAR),
        AttributeDef("hazard_class", AttrKind.ENUM,
                     allowed=("none", "flammable", "corrosive", "toxic", "oxidizer", "irritant")),
        AttributeDef("storage_condition", AttrKind.ENUM,
                     allowed=("room_temp", "refrigerated", "frozen", "dry", "dark")),
        AttributeDef("grade", AttrKind.ENUM,
                     allowed=("reagent", "acs", "hplc", "isotope", "technical")),
        AttributeDef("package_size", AttrKind.SCALAR),
        # field_info 구조 스펙 — 원본 텍스트 그대로 저장하는 scalar 차원 (이슈: field_info 연동)
        AttributeDef("purity", AttrKind.SCALAR, description="field_info purity(원본 텍스트)"),
        AttributeDef("molecular_formula", AttrKind.SCALAR),
        AttributeDef("molecular_weight", AttrKind.SCALAR),
        AttributeDef("boiling_point", AttrKind.SCALAR),
        AttributeDef("melting_point", AttrKind.SCALAR),
        AttributeDef("density", AttrKind.SCALAR),
        AttributeDef("solubility", AttrKind.SCALAR),
        AttributeDef("storage", AttrKind.SCALAR, description="field_info storage(원본 텍스트)"),
        AttributeDef("hazard_statements", AttrKind.SCALAR),
    ),
}

PRODUCT_TYPES: tuple[str, ...] = tuple(VOCABULARY.keys())


def attributes_for(product_type: str) -> dict[str, AttributeDef]:
    return VOCABULARY.get(product_type, {})


def is_controlled(product_type: str, attribute: str) -> bool:
    """어휘에 정의된 차원인가. 아니면 호출자는 '후보'로 처리한다(성장 규칙)."""
    return attribute in VOCABULARY.get(product_type, {})
