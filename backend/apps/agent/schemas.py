"""SSE 이벤트 페이로드 스키마 (이슈 05) — Orval 타입 생성을 위한 OpenAPI 컴포넌트.

실제 /chat 스트림은 Django 뷰가 흘리므로(SSE는 OpenAPI로 표현 불가) 페이로드 형태만
아래 스키마로 문서화한다. 프론트는 이 타입으로 SSE 프레임을 파싱한다.
"""
from __future__ import annotations

from ninja import Schema


class HistoryMessage(Schema):
    """무상태 멀티턴 히스토리 한 줄. role: user | assistant."""
    role: str
    content: str


class ChatIn(Schema):
    """POST /chat 요청 본문."""
    query: str
    history: list[HistoryMessage] = []


class GroundingItem(Schema):
    name: str
    value: str
    provenance: str  # structured | llm_text | vision


class ProductCard(Schema):
    source_id: str
    name: str
    url: str
    image_url: str | None = None
    price_min: int | None = None   # 변형 가격 최저(KRW). 가격 없으면 None
    price_max: int | None = None   # 변형 가격 최고(KRW)
    grounding: list[GroundingItem] = []


class TokenData(Schema):
    """event: token — 추천 근거 토큰 조각."""
    content: str


class RecommendationData(Schema):
    """event: recommendation — 결정적으로 부착된 상품 카드."""
    products: list[ProductCard] = []


class ClarificationData(Schema):
    """event: clarification — 되묻기 문구."""
    question: str


class StatusData(Schema):
    """event: status — 도구 호출 진행 상태(첫 토큰 전 전환형 표시)."""
    label: str


class ErrorData(Schema):
    """event: error — 스트림 내 오류."""
    message: str


class ChatEventCatalog(Schema):
    """SSE 이벤트 페이로드 카탈로그(코드젠 전용)."""
    token: TokenData
    recommendation: RecommendationData
    clarification: ClarificationData
    status: StatusData
    error: ErrorData
