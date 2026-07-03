# 12 — GraphStore 유사도 질의 (pgvector)

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

GraphStore에 **pgvector 유사도 질의**(GraphRAG의 의미 절반, ADR-0003) 추가. 쿼리 임베딩으로 Application·Condition 노드 / Product 텍스트의 근접 항목을 반환. 속성 필터(SQL)·AGE 순회와 더불어 검색의 세 번째 축.

## Acceptance criteria

- [ ] 쿼리 벡터로 top-k 유사 Application/Condition 노드 반환
- [ ] 쿼리 벡터로 top-k 유사 Product 텍스트 반환
- [ ] 모델 버전이 일치하는 임베딩만 비교(차원/모델 혼선 방지)
- [ ] 통합 테스트: 알려진 임베딩으로 기대 순위 반환

## Blocked by

- `11-embedding-module.md`
