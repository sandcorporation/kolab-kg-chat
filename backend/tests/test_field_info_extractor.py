"""field_info → 구조 속성(결정적, provenance=structured)."""
from apps.extraction.field_info import field_info_attributes


def test_field_info_maps_specs_as_structured():
    fi = {
        "purity": ">=99.5% (GC)",
        "cas_number": "29007",
        "molecular_formula": "C3H5NO",
        "storage": "2-8C",
        "boiling_point": "",           # 빈 값 → 스킵
        "product_description": "x",    # 매핑 안 함
    }
    by_name = {a.name: a for a in field_info_attributes(fi)}

    assert by_name["purity"].value == ">=99.5% (GC)"
    assert by_name["purity"].provenance == "structured"
    assert by_name["purity"].is_candidate is False   # 어휘에 있음
    assert by_name["cas_number"].value == "29007"
    assert by_name["molecular_formula"].value == "C3H5NO"
    assert "boiling_point" not in by_name             # 빈 값 제외
    assert "product_description" not in by_name        # 미매핑


def test_field_info_empty_returns_nothing():
    assert field_info_attributes({}) == []
