"""SourceConnector — 소스 DB를 은닉하는 딥모듈 인터페이스 (이슈 04, ADR-0002).

다운스트림(추출·그래프)은 `ProductDocument`만 소비하고 소스(MySQL/영카트)를 모른다.
월요일 실제 DB 교체는 이 인터페이스의 구현만 바꾼다(이슈 26).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Protocol


@dataclass(frozen=True)
class SourceImage:
    url: str
    position: int
    source: str = "gallery"   # "gallery"(it_img1~n) | "explan"(it_explan 임베디드)


@dataclass(frozen=True)
class SourceVariant:
    """한 Product의 구매 가능한 형태(옵션). cosmetic/functional 판정은 하지 않는다(이슈 08/09)."""

    variant_key: str          # 소스에서 안정적인 변형 식별자
    label: str                # 원형 옵션 라벨
    price: int | None         # 절대 가격(KRW). 소스의 가격 delta는 커넥터가 해소한다.
    raw: dict


@dataclass(frozen=True)
class ProductDocument:
    """소스 무관(source-agnostic) 조립 상품. 스왑 seam의 출력 계약."""

    source_id: str            # 멱등 upsert 키(ADR-0008)
    name: str
    brand: str | None
    category_path: list[str]
    description_text: str
    images: list[SourceImage]
    variants: list[SourceVariant]
    content_hash: str         # content-hash 게이팅용(ADR-0008)
    raw: dict                 # 원본 escape hatch
    fetched_at: datetime


@dataclass(frozen=True)
class ProductChanged:
    source_id: str
    op: str                   # "created" | "updated" | "deleted"


class SourceConnector(Protocol):
    """소스 → ProductDocument 의 좁은 인터페이스(딥모듈)."""

    def iter_product_ids(self) -> AsyncIterator[str]:
        """초기 전체 적재용 — 모든 Product 식별자를 산출한다."""
        ...

    async def assemble(self, source_id: str) -> ProductDocument | None:
        """소스의 현재 상태를 재조립해 ProductDocument를 만든다(멱등, ADR-0008)."""
        ...

    def subscribe_changes(self) -> AsyncIterator[ProductChanged]:
        """소스 변경 스트림(CDC). 이슈 14(폴러)·26(실제 CDC)에서 구현."""
        ...
