# 03 — GraphStore 배치 세션(커넥션 재사용 + 배치 커밋)

Status: done

## Parent
`.scratch/low-resource-scale-ingest/PRD.md`

## What to build

배치 동안 하나의 Postgres 커넥션(+`LOAD 'age'`·search_path 1회)을 재사용하고 배치 단위로 커밋하는 세션 모드를 GraphStore에 추가한다. 기존의 "메서드마다 새 커넥션+autocommit" 대신, 주입된 공용 커넥션 위에서 쓰기 메서드가 실행되고 명시적 커밋을 받는다. 대량 적재 세션은 `synchronous_commit=off`. 세션 밖 단건 사용(기존 API)은 그대로 동작.

## Acceptance criteria

- [ ] 배치 세션으로 N개 상품을 처리하면 커넥션이 상품마다가 아니라 배치당 1회 열린다(주입 카운팅 팩토리로 검증)
- [ ] 배치 커밋 후 데이터가 보인다(멱등 upsert 유지)
- [ ] 세션 밖 기존 단건 메서드 호출도 그대로 동작(회귀 없음)

## Blocked by
None - can start immediately
