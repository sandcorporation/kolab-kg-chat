# 25 — 100 동시 하드닝 + 부하 테스트

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

100 동시 챗을 견디는 하드닝(ADR-0007). **Postgres 커넥션 풀링**(asyncpg/pgbouncer), **uvicorn 다중 레플리카** behind LB, 이벤트루프 비차단 점검(동기 ORM/IO 누수 색출). 100 동시 스트리밍 부하 테스트로 검증.

## Acceptance criteria

- [ ] DB 커넥션 풀로 챗당 커넥션 개방 방지(max_connections 미초과)
- [ ] uvicorn 2+ 레플리카가 LB 뒤에서 동작(모델 A라 Redis 불필요)
- [ ] async 경로에 동기 블로킹 호출 없음(점검/테스트)
- [ ] 부하 테스트: 100 동시 스트리밍 챗이 끊김 없이 처리됨
- [ ] 인스턴스 1개 다운 시 나머지가 신규 연결 수용

## Blocked by

- `24-openai-concurrency-limiter.md`
