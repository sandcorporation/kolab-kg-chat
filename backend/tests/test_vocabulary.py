"""이슈 05 — 유형별 통제 어휘 시드 구조 검증."""
from apps.extraction.vocabulary import (
    AttrKind,
    PRODUCT_TYPES,
    attributes_for,
    is_controlled,
)


def test_product_types_cover_seed_domains():
    assert set(PRODUCT_TYPES) == {
        "glassware_consumable",
        "electronic_instrument",
        "reagent_chemical",
    }


def test_glassware_has_decisive_dimensions():
    attrs = attributes_for("glassware_consumable")
    assert attrs["material"].kind is AttrKind.ENUM
    assert attrs["temperature_max"].kind is AttrKind.NUMERIC_RANGE
    assert attrs["temperature_max"].unit == "℃"
    assert attrs["light_protection"].kind is AttrKind.BOOLEAN  # 차광 함정 차원


def test_reagent_has_cas_and_purity():
    attrs = attributes_for("reagent_chemical")
    assert attrs["cas_number"].kind is AttrKind.SCALAR
    assert attrs["purity_percent"].kind is AttrKind.NUMERIC_RANGE


def test_is_controlled_distinguishes_known_and_candidate():
    assert is_controlled("glassware_consumable", "material") is True
    # 어휘에 없는 차원 → 후보(성장 규칙)
    assert is_controlled("glassware_consumable", "unknown_dimension") is False
