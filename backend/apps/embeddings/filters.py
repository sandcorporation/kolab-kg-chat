"""숫자 범위 하드 필터 레지스트리 (ADR-0018).

임베딩이 못 하는 것 = 숫자 범위 비교. 각 필터를 (이름, doc→(min,max) 추출)로 선언하고,
적재·색인·질의가 이 레지스트리 위에서 일반화된다. 범주형(브랜드·재질 등)은 임베딩이 처리하므로
여기 없다. 값이 없거나 파싱 실패면 (None,None) → 그 상품은 해당 필터에서 제외(NULL).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

# 범위 구분 '-'(2-8)와 음수 '-'(-20)를 구분: 숫자 뒤 '-'는 음수로 안 봄.
_NUM = re.compile(r"(?<!\d)-?\d+(?:\.\d+)?")


def _numbers(text: str) -> list[float]:
    return [float(x) for x in _NUM.findall(text or "")]


def parse_range(text: str) -> tuple[float | None, float | None]:
    """텍스트에서 숫자를 뽑아 (min,max). 하나면 point(min=max). 없으면 (None,None)."""
    nums = _numbers(text)
    if not nums:
        return (None, None)
    return (min(nums), max(nums))


def parse_storage_temp(text: str) -> tuple[float | None, float | None]:
    """보관온도: 숫자 범위면 그대로("2-8C"→(2,8)), 없으면 소어휘 매핑(실온→15~25)."""
    nums = _numbers(text)
    if nums:
        return (min(nums), max(nums))
    t = (text or "").lower()
    if "room" in t or "ambient" in t or "실온" in t or "상온" in t:
        return (15.0, 25.0)
    return (None, None)


def _field_info(doc, field: str) -> str:
    """변형들의 raw.field_info에서 field 값을 찾는다(상품 레벨, 첫 값)."""
    for v in getattr(doc, "variants", None) or []:
        fi = (getattr(v, "raw", None) or {}).get("field_info")
        if fi and fi.get(field):
            return str(fi[field])
    return ""


def _price(doc) -> tuple[float | None, float | None]:
    prices = [v.price for v in (getattr(doc, "variants", None) or []) if getattr(v, "price", None)]
    return (float(min(prices)), float(max(prices))) if prices else (None, None)


@dataclass(frozen=True)
class FilterSpec:
    name: str
    kind: str  # "range" (모두 숫자 범위)
    extract: Callable[[object], tuple]


FILTER_SPEC: list[FilterSpec] = [
    FilterSpec("price", "range", _price),
    FilterSpec("purity", "range", lambda d: parse_range(_field_info(d, "purity"))),
    FilterSpec("molecular_weight", "range", lambda d: parse_range(_field_info(d, "molecular_weight"))),
    FilterSpec("storage_temp", "range", lambda d: parse_storage_temp(_field_info(d, "storage"))),
]

# 적재·검색이 공유하는 컬럼 목록(각 필터 _min·_max).
FILTER_COLUMNS: list[str] = [f"{f.name}_min" for f in FILTER_SPEC] + [
    f"{f.name}_max" for f in FILTER_SPEC
]


def extract_filters(doc) -> dict[str, tuple[float | None, float | None]]:
    """상품 doc → {필터이름: (min,max)}. 값 없는 필터는 생략."""
    out: dict[str, tuple] = {}
    for f in FILTER_SPEC:
        lo, hi = f.extract(doc)
        if lo is not None or hi is not None:
            out[f.name] = (lo, hi)
    return out
