"""추천 API 라우터 — SSE 이벤트 페이로드 스키마 문서화(Orval 코드젠용).

실제 대화는 스트리밍 뷰 POST /chat이 처리한다(SSE). 읽기 경로는 Recommendation
Agent 단일화됨(ADR-0011) — 구 비스트리밍 /recommend 파이프라인은 제거되었다.
"""
from ninja import Router

from apps.agent.schemas import (
    ChatEventCatalog,
    ChatIn,
    ClarificationData,
    ErrorData,
    RecommendationData,
    TokenData,
)

router = Router()


@router.post("/chat/schema", response=ChatEventCatalog)
async def chat_event_schema(request, payload: ChatIn):
    """코드젠 전용: POST /chat 요청 본문(ChatIn)과 SSE 이벤트 페이로드 타입을 노출한다."""
    return ChatEventCatalog(
        token=TokenData(content=""),
        recommendation=RecommendationData(products=[]),
        clarification=ClarificationData(question=""),
        error=ErrorData(message=""),
    )
