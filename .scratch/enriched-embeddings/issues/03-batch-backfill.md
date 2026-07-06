# 이슈 03: Batch API 대량 강화 명령

Status: ready-for-agent
Type: AFK
Parent: .scratch/enriched-embeddings/PRD.md

## What to build

전체 카탈로그(수십만) 최초 강화를 저렴·안정적으로 하는 backfill 명령. 강화가 필요한 상품(신규·변경·미강화)을 모아 **OpenAI Batch API**로 설명을 제출한다(비동기·24h·**50% 비용**) — 제출 → 폴링 → 완료 시 설명 저장(DescriptionStore) + 재임베딩. 카탈로그가 작으면 `--sync`로 동시성 기반 즉시 처리도 지원. 진행·재개 안전(중간 실패 시 이미 강화된 건 건너뜀 = content-hash). 비용 외삽: 628k 표준 ~$42 / Batch ~$21(1회성).

## Acceptance criteria

- [ ] 강화 대상 선별(미강화/변경분만 — content-hash)
- [ ] Batch 경로: 프롬프트 제출 → 폴링 → 결과 설명 저장 + 재임베딩
- [ ] `--sync` 경로: 동시성 기반 즉시 강화(소규모용)
- [ ] 재개 안전: 중단 후 재실행 시 이미 강화된 건 스킵
- [ ] 프롬프트 빌드·결과 파싱 결정적 테스트(Batch 제출 mock)
- [ ] 라이브: 소량으로 Batch/sync 한 경로 검증

## Blocked by

- 이슈 01 (DescriptionGenerator + 캐시)
