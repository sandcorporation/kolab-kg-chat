# 05 — 계층화 쿼리셋(능력 태그)

Status: done — EvalQueries + 27개 계층화 쿼리(keyword7·structured10·semantic10) 실제 코퍼스 근거로 작성·적재. vision·compatibility 계층은 데이터 제약으로 제외. 테스트 test_eval_queries(2).

## Parent
`.scratch/retrieval-quality-eval/PRD.md`

## What to build

코퍼스 기반 계층화 쿼리셋(~24-30). 각 쿼리에 탐침 능력 태그: `structured`(속성 필터로 답)·`vision`(스펙이 이미지에만)·`semantic`(한/영·유의어 미스매치)·`compatibility`(호환/부속). 한/영 혼합, **코퍼스에 답이 실제로 존재**하도록 작성. 초안은 에이전트가 코퍼스에서 뽑아 만들고, 사람이 도메인 타당성을 검토·승인한다(HITL).

## Acceptance criteria

- [ ] ~24-30 쿼리가 4개 능력 태그에 고루 분포한다
- [ ] 각 쿼리는 코퍼스 안에 적합한 답(상품)이 존재한다
- [ ] 한/영 쿼리가 모두 포함된다
- [ ] 사람 검토·승인을 거쳐 영속된다

## Blocked by
- 00 (코퍼스)
