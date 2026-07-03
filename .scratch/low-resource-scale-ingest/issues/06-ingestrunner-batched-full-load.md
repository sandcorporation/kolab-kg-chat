# 06 — IngestRunner 배치 full_load

Status: done

## Parent
`.scratch/low-resource-scale-ingest/PRD.md`

## What to build

`full_load`를 키셋 스트리밍(04) + 배치 세션(03) + 배치당 커밋으로 재구성한다. 배치 크기 기본 500, `INGEST_BATCH_SIZE`/`--batch-size`로 조절. 상품은 1건씩 처리·해제(순차). 결과(전량 적재·멱등·속성 반영)는 기존과 동일하되 커넥션·메모리·시간이 규모에 확장 가능해야 한다.

## Acceptance criteria

- [ ] `full_load`가 전량 적재·멱등(재실행 시 중복 없음)
- [ ] 배치 단위 커밋(배치당 커넥션 1회 — 카운팅 검증)
- [ ] `--batch-size`/`INGEST_BATCH_SIZE`로 배치 크기 조절
- [ ] 기존 인제스트 동작(속성 반영 등) 회귀 없음

## Blocked by
- 03 (배치 세션), 04 (키셋 스트리밍)
