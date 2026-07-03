# 05 — changed_since(it_update_time) + SyncWatermark

Status: done

## Parent
`.scratch/low-resource-scale-ingest/PRD.md`

## What to build

증분 감지 기반. (a) mock `g5_shop_item`에 `it_update_time`(및 `it_time`) 컬럼·값 추가. (b) 커넥터에 `it_update_time > watermark`인 변경 Product id를 산출하는 조회와 관측 최대 `it_update_time` 반환. (c) **SyncWatermark**: 작은 Postgres 테이블(`sync_state`, key→value)에 마지막 watermark를 영속(get/set). `it_update_time` 컬럼이 없으면 감지 불가 신호를 낸다(워커가 재조정으로 폴백하도록).

## Acceptance criteria

- [ ] mock 스키마·시드에 `it_update_time`이 있다
- [ ] `changed_since(watermark)`가 watermark 이후 변경 Product만 산출한다
- [ ] SyncWatermark set→get 왕복, 재시작(새 인스턴스)에서도 값 유지
- [ ] `it_update_time` 부재 시 폴백 신호(예외/센티넬)로 알린다

## Blocked by
None - can start immediately
