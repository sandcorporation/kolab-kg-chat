# 이슈 05: eval A/B — 강화 vs 현행 (± 분석기), 판정관 채점

Status: ready-for-agent
Type: HITL
Parent: .scratch/enriched-embeddings/PRD.md

## What to build

강화가 실제 추천 품질을 올리는지 **판정관(gpt-4o) 채점**으로 확정한다(recall이 아니라 최종 품질). eval 하네스로 강화 임베딩(별도 테이블, 예 `eval_embedding_rich`)을 만들고, 네 조합을 A/B: **현행+분석기 / 강화+분석기 / 현행+분석기없음 / 강화+분석기없음**. 절대 적합도·승률로 비교하고, (a) 강화가 품질을 올리는지, (b) 강화 시 분석기를 빼도(채팅당 2→1 LLM) 품질이 유지되는지 판정한다. 프로토타입 recall(2→10, 12→13)의 판정관 확증. 결과로 **질의 경로 분석기 토글** 확정 여부를 결정(HITL).

## Acceptance criteria

- [ ] eval 코퍼스에 강화 임베딩(별도 테이블)으로 config 추가(현행과 공존)
- [ ] 4조합 A/B 실행 — 절대점수·승률
- [ ] 강화가 품질↑인지, 분석기 제거 시 유지되는지 판정, RESULTS 기록
- [ ] 분석기 토글(비용↓ vs 품질) 확정/보류 근거 명시

## Blocked by

- 이슈 02 (적재 통합)
- 이슈 03 (대량 강화로 코퍼스 강화)
