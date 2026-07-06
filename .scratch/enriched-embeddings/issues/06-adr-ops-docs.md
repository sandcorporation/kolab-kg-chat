# 이슈 06: ADR + 운영/문서

Status: ready-for-agent
Type: AFK
Parent: .scratch/enriched-embeddings/PRD.md

## What to build

되돌리기 비용·트레이드오프(적재 LLM 비용 ↔ 채팅 비용 절감·검색 품질)를 **짧은 ADR 1건**으로 남긴다 — ADR-0012(임베딩)·0014(RAG)를 확장, A/B 근거·비용 외삽·분석기 토글 결정 포함. `.env.example`에 `RAG_ENRICH`·`RAG_DESCRIPTION_MODEL` 문서화. README 적재 절에 강화(설명 임베딩)·Batch backfill·프롬프트 캐싱 관측 반영. 원칙 재확인: 임베딩은 검색 리콜용, 카드 그라운딩·가격·URL은 결정적 부착 유지(ADR-0001).

## Acceptance criteria

- [ ] ADR 신규 1건(강화 결정·A/B 결과·비용·분석기 토글, 0012/0014 확장)
- [ ] .env.example에 RAG_ENRICH·RAG_DESCRIPTION_MODEL
- [ ] README에 강화·Batch backfill·캐싱 관측 반영
- [ ] 전체 스위트 그린

## Blocked by

- 이슈 05 (A/B 결과)
