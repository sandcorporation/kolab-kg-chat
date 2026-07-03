# 17 — Retriever 유사도 다리

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

Retriever에 **pgvector 유사도 다리**(질문 9-A)를 추가. "비슷한 응용/환경"을 그래프 순회가 아니라 **Application·Condition 임베딩 유사도**(#12)로 건너뛴다. 정확 속성 매칭이 빈약할 때 의미적으로 가까운 응용을 통해 후보를 확장한다(GraphRAG).

## Acceptance criteria

- [ ] 질의 응용과 유사한 Application/Condition을 임베딩으로 회수
- [ ] 회수된 유사 응용을 통해 후보 Product 확장
- [ ] 속성 필터(#16) 결과와 유사도 결과가 결합됨
- [ ] 근거에 "정확 매칭" vs "유사 응용 경유"가 구분 표기됨
- [ ] 통합 테스트: 정확 매칭 0건이어도 유사 경유로 후보 반환

## Blocked by

- `12-graphstore-similarity-query.md`
- `16-retriever-attribute-filter-composer.md`
