"""이슈 05 — OpenAPI가 SSE 이벤트 페이로드 스키마를 노출한다(Orval 코드젠 대상)."""
from django.test import AsyncClient


async def test_openapi_exposes_sse_payload_schemas():
    client = AsyncClient()
    schemas = (await client.get("/openapi.json")).json()["components"]["schemas"]

    # 프론트가 SSE 프레임을 타입 안전하게 파싱할 수 있도록 핵심 페이로드가 노출된다.
    assert "ProductCard" in schemas
    assert "GroundingItem" in schemas
    assert "RecommendationData" in schemas
    assert "TokenData" in schemas
    assert "ChatIn" in schemas

    card = schemas["ProductCard"]["properties"]
    assert set(["source_id", "name", "url", "image_url", "grounding"]) <= set(card)
