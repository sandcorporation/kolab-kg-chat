# 01 — Reranker 딥모듈 (LLMReranker + FakeReranker)

Status: done

## Parent

`.scratch/rerank-query-normalization/PRD.md`

## What to build

검색과 선택 사이에 들어갈 `Reranker` 딥모듈과 그 첫 구현 `LLMReranker`, 테스트용 `FakeReranker`.
질의와 후보 리스트를 받아 후보마다 질의 적합도 0~3 점수를 매기고, 임계 이상만 점수순으로 남긴다.
`LLMReranker`는 gpt-4o-mini에 후보 전체(이름 + 설명 + 레지스트리 값)를 **한 번의 배치 콜**로 넣어
후보별 점수를 파싱한다(후보당 콜 아님). 후보 수가 노출 상한 이하이면 자를 게 없으므로 LLM 콜을
생략한다(스킵 최적화). 이 슬라이스는 파이프라인에 연결하지 않는 격리 딥모듈이다.

점수 의미(확정): `0` 무관 · `1` 약함 · `2` 적합 · `3` 매우 적합. 기본 컷 `≥2`, 기본 상한 10.

## Acceptance criteria

- [ ] `rerank(query, candidates)`가 후보별 점수를 매기고 점수 내림차순으로 정렬해 반환
- [ ] 점수 < 임계(기본 2) 후보는 제외하고, 노출 상한(기본 10)까지만 남김
- [ ] 후보 수가 상한 이하이면 LLM 콜 없이 통과(스킵 최적화)
- [ ] `FakeReranker`로 결정적 테스트 가능, `LLMReranker`는 fake 모델(캔드 점수)로 파싱·정렬·임계 검증
- [ ] 점수 응답이 형식에서 이탈해도 견고(누락 후보는 0점 취급 등)
- [ ] 임계·상한·모델은 설정(env 기본)으로 주입 가능

## Blocked by

None - can start immediately
