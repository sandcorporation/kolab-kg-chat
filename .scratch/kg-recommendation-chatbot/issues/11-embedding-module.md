# 11 — EmbeddingModule

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

**EmbeddingModule**(ADR-0009): Application·Condition 노드(이름+정의)와 Product 서술 텍스트를 `text-embedding-3-small`로 임베딩해 pgvector에 저장한다. 모든 임베딩에 **모델/버전 태그**를 부착해, 모델 교체 시 점진 재임베딩이 가능하게 한다. 테스트는 결정적 임베딩 더블.

## Acceptance criteria

- [ ] Product 서술 텍스트 임베딩이 pgvector 컬럼에 저장됨
- [ ] Application·Condition 노드 임베딩 저장(질문 9-A 의미 다리용)
- [ ] 각 임베딩에 모델 버전 태그 기록
- [ ] 모델 버전이 바뀐 항목만 재임베딩 대상으로 식별됨
- [ ] 가짜 임베딩 제공자로 결정적 테스트

## Blocked by

- `06-graphstore-upsert.md`
