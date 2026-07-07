# 02 — 후보에 레지스트리 값 부착 + 검색 폭 50

Status: ready-for-agent

## Parent

`.scratch/rerank-query-normalization/PRD.md`

## What to build

`HybridRetriever`가 각 후보에 레지스트리 값(가격·순도·분자량·보관온도)을 실어 반환하고, 검색 폭을
50으로 넓힌다. 이를 위해 `EmbeddingStore`/`SemanticSearch`의 검색 결과 SELECT에 레지스트리 컬럼을
포함시킨다. 리랭커가 이 숫자 값을 보고 살아남은 후보들 사이의 소프트 정렬(더 저렴/고순도/근접
스펙)을 하도록 하는 준비 단계다. 숫자 하드 필터(ADR-0018)는 검색 시점에 그대로 동시 적용된다.

## Acceptance criteria

- [ ] retrieve 결과의 각 후보에 레지스트리 4종 값이 실려 있음(값 없으면 None)
- [ ] 검색 폭이 50(env로 조정 가능)
- [ ] 숫자 하드 필터가 여전히 검색 시점에 함께 적용됨(회귀 없음)
- [ ] 기존 후보 필드(이름·설명 부착)와 하이브리드 합집합·중복제거 동작 불변
- [ ] `test_hybrid_retriever.py`류로 후보가 레지스트리 값을 실어오는지 검증

## Blocked by

None - can start immediately
