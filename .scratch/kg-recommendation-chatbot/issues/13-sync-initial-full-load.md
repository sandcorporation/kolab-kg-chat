# 13 — SyncOrchestrator: 초기 전체 적재

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

**SyncOrchestrator**의 초기 전체 적재 경로(ADR-0008). `iter_product_ids()`로 모든 Product를 enqueue → 워커가 assemble→extract(텍스트+비전)→upsert. delta와 동일한 워커 경로를 쓴다. 워커는 챗 읽기 경로와 분리(ADR-0007). 큐는 taskiq.

## Acceptance criteria

- [ ] "전체 재적재" 트리거가 시드 4종을 모두 enqueue
- [ ] 워커가 각 Product를 assemble→extract→upsert로 처리
- [ ] 적재 후 그래프에 4종 + 속성(텍스트/이미지) 존재
- [ ] 재실행해도 멱등(중복 노드 없음)
- [ ] 워커가 API(챗) 프로세스와 분리 실행됨

## Blocked by

- `08-attribute-extractor-text.md`
