# 07 — Orval 타입드 클라이언트

Status: done — `frontend/orval.config.ts` + 생성된 `frontend/src/api/`(ProductCard 등 모델).

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

Orval을 설정해 백엔드 OpenAPI(`/openapi.json`)에서 **TS 타입 + REST 클라이언트**를 생성한다(추천 카드 페이로드 타입 포함). SSE 소비는 Orval 대상이 아니므로 수제 리더가 쓰되, **이벤트 페이로드 타입은 Orval 생성분을 사용**한다.

## Acceptance criteria

- [ ] Orval 설정(입력=OpenAPI) + 생성 스크립트
- [ ] recommendation 카드 타입 등 생성물이 프론트에서 import 가능
- [ ] 비스트리밍 REST(있으면) 클라이언트 생성
- [ ] 생성물이 타입체크 통과

## Blocked by
- `05-openapi-sse-schemas.md`
- `06-react-scaffold-nginx.md`
