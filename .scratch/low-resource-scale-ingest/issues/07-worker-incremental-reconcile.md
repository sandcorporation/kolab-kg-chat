# 07 — 워커 증분 + 주기적 재조정

Status: done

## Parent
`.scratch/low-resource-scale-ingest/PRD.md`

## What to build

`sync_poll`을 증분 우선으로 재구성한다. 평소엔 `changed_since(watermark)`로 바뀐 Product만 assemble·반영(content_hash 게이팅 유지)하고 watermark를 전진. 저빈도(예: 야간 1회)로 전체 재조정을 돌려 하드 삭제·드리프트를 배치 스트리밍으로 보정한다. `it_update_time` 부재 시 재조정으로 폴백. 빈 소스 안전장치 유지.

## Acceptance criteria

- [ ] 증분: 한 Product의 `it_update_time`만 올리면 그 상품만 updated로 감지·반영, watermark 전진
- [ ] 재조정: 소스에 없는(삭제된) 상품을 그래프에서 제거
- [ ] 빈 소스면 전량 삭제하지 않는다(가드 유지)
- [ ] `it_update_time` 부재 시 재조정 경로로 폴백
- [ ] `--once`/주기 실행 옵션 유지

## Blocked by
- 05 (changed_since + watermark), 06 (배치 러너)
