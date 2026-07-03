# 22 — Widget 스켈레톤 + Orval + SSE 토큰 렌더

Status: ready-for-human

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

React 챗 위젯의 골격. **Orval**로 Django Ninja OpenAPI에서 타입+비스트리밍 REST 클라이언트를 생성(ADR-0007, 플랜 6). SSE 스트림은 얇은 수제 리더(EventSource/fetch)로 소비해 `token` 이벤트를 이어 붙여 표시한다. 챗 UX/디자인 방향에 사람 리뷰가 필요하므로 HITL.

## Acceptance criteria

- [ ] Orval 설정으로 OpenAPI → TS 타입 + REST 클라이언트 생성
- [ ] SSE 이벤트 페이로드 타입이 OpenAPI components에서 생성됨
- [ ] 수제 SSE 리더가 `token`을 실시간으로 이어 붙여 렌더
- [ ] `done`/`error` 처리
- [ ] 디자인 리뷰 통과(UX 방향 승인)

## Blocked by

- `19-sse-streaming.md`
