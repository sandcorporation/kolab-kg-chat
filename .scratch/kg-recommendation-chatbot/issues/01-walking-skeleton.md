# 01 — Django Ninja walking skeleton + docker

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

Django + Django Ninja 프로젝트를 ASGI(uvicorn)로 띄우는 걸어다니는 골격. `/health`가 200을 반환하고 OpenAPI 스키마가 생성된다. docker-compose로 `api` 서비스가 뜬다. 전 구간 async 규율의 출발점(ADR-0006).

## Acceptance criteria

- [ ] `docker compose up` 으로 `api` 컨테이너가 뜬다
- [ ] `GET /health` → 200, `{"status":"ok"}` (async 뷰)
- [ ] Django Ninja OpenAPI 스키마가 노출된다(`/api/openapi.json` 등)
- [ ] uvicorn ASGI로 구동된다(WSGI 아님)
- [ ] health 엔드포인트 테스트 1개 통과(async 테스트 클라이언트)

## Blocked by

None - can start immediately
