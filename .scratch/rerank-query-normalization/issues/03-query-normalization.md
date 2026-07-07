# 03 — 질의 정규화 강화 (QueryAnalyzer)

Status: ready-for-agent

## Parent

`.scratch/rerank-query-normalization/PRD.md`

## What to build

`QueryAnalyzer`의 분석 프롬프트를 강화해 질의를 일관되게 정규화한다: (a) 조사·의문 제거
("집게 있어?"→"집게"), (b) KO/EN 키워드 항상 생성(짧은 질의도 비대칭 없이), (c) 동의어·유형
확장(집게→tong/clamp/forceps/retriever). 리랭커가 정밀도를 뒤에서 받치므로 리콜 지향으로 넓게
확장한다. 반환 구조·인터페이스(keywords/semantic/filters/followup)는 불변이다.

진단 근거: 현행은 "집게 있어?"→키워드 `['집게 있어?']`(확장 없음) vs "자석집게는?"→키워드 3개로
비대칭 확장 → 넓은 질의의 리콜이 오히려 빈약.

## Acceptance criteria

- [ ] "집게 있어?" 같은 질의에서 조사/의문이 제거된 핵심어가 키워드에 포함
- [ ] 짧은 질의도 KO/EN 키워드가 일관되게 생성(비대칭 확장 해소)
- [ ] 동의어·유형 확장이 키워드에 반영
- [ ] fake 모델 구조 출력으로 정규화 동작을 결정적으로 테스트
- [ ] 기존 필터 추출·팔로업 라우팅·검색어 보존 회귀 없음

## Blocked by

None - can start immediately
