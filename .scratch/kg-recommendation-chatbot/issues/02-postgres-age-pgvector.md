# 02 — Postgres + AGE + pgvector 프로비저닝

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

docker-compose에 Postgres를 추가하고 **Apache AGE**와 **pgvector** 확장을 활성화한다(ADR-0003). `/health`가 DB 연결과 두 확장 존재를 async로 확인한다. AGE/pgvector 셋업 마이그레이션이 멱등하게 실행된다.

## Acceptance criteria

- [ ] Postgres 컨테이너가 뜨고 AGE·pgvector 확장이 `CREATE EXTENSION`으로 활성화된다
- [ ] async DB 드라이버(psycopg3 async / asyncpg)로 접속한다(동기 ORM이 이벤트루프를 막지 않음)
- [ ] `GET /health`가 DB 연결 + AGE + pgvector 가용을 확인해 보고한다
- [ ] 확장 활성화 마이그레이션은 재실행해도 안전(멱등)
- [ ] 통합 테스트: 컨테이너 대상 AGE 그래프 생성 + pgvector 벡터 컬럼 trivial 쿼리 성공

## Blocked by

- `01-walking-skeleton.md`
