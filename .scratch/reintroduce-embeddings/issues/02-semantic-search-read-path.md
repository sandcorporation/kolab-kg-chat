# 02 — 운영 읽기 경로에 semantic_search 배선

Status: ready-for-agent

## Parent
`.scratch/reintroduce-embeddings/PRD.md`

## What to build

운영 Recommendation Agent(ADR-0011)가 `semantic_search` 도구를 그래프 도구와 함께 쓰도록 컨텍스트 조립을 바꾼다. 도구는 운영 knowledge_graph의 임베딩 저장소(01)를 가리킨다. 에이전트는 이미 `semantic_tool` 주입을 지원하므로(실험 config4 검증), 운영 컨텍스트에서 이를 연결한다. `/chat`에서 서술형 질의가 semantic_search를 활용해 후보를 넓힌다.

## Acceptance criteria

- [ ] 운영 에이전트 컨텍스트가 semantic_search 도구를 포함한다
- [ ] 서술형 질의(키워드 미스매치)에서 semantic_search가 관련 상품을 후보에 넣는다(라이브 검증)
- [ ] 기존 그래프 도구(search/find/compatible/get_attributes)와 공존하고 회귀 없음
- [ ] 운영 읽기 경로 단일화(ADR-0011)는 유지 — 도구만 추가

## Blocked by
- 01 (EmbeddingStore + 백필로 임베딩 데이터 존재)
