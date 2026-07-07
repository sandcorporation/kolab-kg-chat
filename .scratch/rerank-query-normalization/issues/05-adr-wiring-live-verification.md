# 05 — ADR-0019 + 배선/설정 + 라이브 검증·회귀

Status: done

## Parent

`.scratch/rerank-query-normalization/PRD.md`

## What to build

리랭크 스테이지 도입을 문서화하고, 배선·설정을 마무리한 뒤, 라이브 코퍼스에서 문제 해소와
회귀 없음을 확인한다. ADR-0019에 결정 근거를 기록한다: 리콜/정밀 분리, 리랭커 주도(선택 LLM
강등), 교체 가능한 `Reranker` 인터페이스, LLM 리랭커 vs 로컬 크로스인코더 트레이드오프.
runtime 조립부에서 리랭커를 주입하고 env 노브(검색 폭·`RERANK_TOP_K`·`RERANK_MIN_SCORE`·
리랭커 모델)를 배선한다.

## Acceptance criteria

- [ ] `docs/adr/0019-*.md` 작성(리콜/정밀 분리·리랭커 주도·선택 강등·교체 인터페이스·트레이드오프)
- [ ] runtime이 `RagRecommender`에 리랭커를 주입하고 env 노브가 반영됨
- [ ] 라이브 "집게 있어?"가 집게류를 여럿 반환(1개 → 다수)
- [ ] 라이브 "자석집게는?"의 무관 결과(방석·선반 등) 감소
- [ ] 기존 질의(원심분리기·건식실리카겔·마우스케이지 등) 회귀 없음(스팟 체크)
- [ ] 전체 테스트 스위트 그린

## Blocked by

- `.scratch/rerank-query-normalization/issues/04-rerank-stage-in-recommender.md`
- `.scratch/rerank-query-normalization/issues/03-query-normalization.md`
