# 04 — Source Connector 키셋 스트리밍 + 커넥션 재사용

Status: done

## Parent
`.scratch/low-resource-scale-ingest/PRD.md`

## What to build

`iter_product_ids`를 `it_id` 키셋 페이지네이션으로 바꿔 전량 버퍼링을 없앤다(배치 크기만큼씩 fetch). `assemble`은 배치 동안 소스 커넥션을 재사용할 수 있어야 한다(주입 가능). 결과·순서·`limit` 의미는 보존.

## Acceptance criteria

- [ ] `iter_product_ids`가 모든 it_id를 순서대로 산출한다(누락·중복 없음)
- [ ] `limit`가 여전히 상한으로 동작한다
- [ ] 전체 id를 한 번에 버퍼링하지 않고 청크 단위로 가져온다
- [ ] 배치 동안 소스 커넥션 재사용(상품마다 새 커넥션 아님, 카운팅으로 검증)

## Blocked by
None - can start immediately
