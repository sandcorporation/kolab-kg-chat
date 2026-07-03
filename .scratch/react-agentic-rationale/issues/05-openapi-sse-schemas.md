# 05 — OpenAPI SSE 페이로드 스키마 (Orval용)

Status: done — `apps/agent/schemas.py` + api.py의 코드젠 엔드포인트, 테스트 `tests/test_openapi_sse_schema.py` 통과.

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

SSE 이벤트 페이로드(특히 `recommendation`의 상품 카드 타입)와 REST 요청/응답을 Django Ninja Schema로 정의해 **OpenAPI(components)에 노출**한다. SSE 자체는 스트림이라 OpenAPI로 모델링 안 되지만, **페이로드 타입은 노출**해 Orval이 TS 타입을 생성하게 한다.

## Acceptance criteria

- [ ] recommendation 상품 카드 스키마(source_id/name/url/image_url/grounding)가 OpenAPI에 노출
- [ ] clarification 등 이벤트 페이로드 스키마 노출
- [ ] `/openapi.json`에 위 스키마가 포함됨
- [ ] 기존 엔드포인트 회귀 없음

## Blocked by
- `01-product-enricher.md`
