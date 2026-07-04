# 이슈 03: eval 하네스 복원 + RAG config + A/B 실행 (게이트)

Status: done — eval 하네스 복원(데이터 존속) + rag config 추가. A/B: RAG 절대 1.968 vs 에이전트 1.871, 승률 0.387 vs 0.226(semantic 0.6 vs 0.2). RAG≥에이전트 → 컷오버 진행.
Type: HITL
Parent: .scratch/rag-recommender/PRD.md

## What to build

RAG를 읽기 경로로 확정하기 전 **품질 게이트**. eval 하네스(`apps/eval`, 250 코퍼스·31 질의·LLM 심사)를 eval 브랜치에서 복원하고, RAG를 **새 config**로 추가한다(config5 HybridReranker와 달리 재랭크가 아니라 LLM 읽기·선택이므로 구분). 필요 시 eval 코퍼스 재구축(build_eval_corpus·embed_corpus). 기준선 **config4(에이전트+embeddings, 최고 2.42)** 와 RAG를 **절대 적합도·승률·지연**으로 A/B하고 RESULTS를 기록한다.

## Acceptance criteria

- [ ] apps/eval 복원 + RAG config 추가(HybridRetriever+RagRecommender를 eval_graph에 물림)
- [ ] eval 코퍼스/임베딩 준비(필요 시 재구축)
- [ ] config4(에이전트) vs RAG A/B 실행 — 절대점수·승률·평균 지연
- [ ] 결과를 RESULTS에 기록하고 채택 여부 판단(RAG ≥ 에이전트인가)
- [ ] 판단 결과를 이슈 04(컷오버)의 진행/보류 근거로 명시

## Blocked by

- 이슈 02 (RagRecommender)
