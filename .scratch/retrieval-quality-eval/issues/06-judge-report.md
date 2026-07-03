# 06 — Judge(블라인드 쌍별·순서스왑, 캐시) + 계층 승률 리포트

Status: done — Judge+aggregate+run_eval, 전체 실행 완료(108 답변·324 심사, 캐시). 결과: RESULTS.md. 테스트 test_eval_judge(3).

## Parent
`.scratch/retrieval-quality-eval/PRD.md`

## What to build

실험의 산출물. config 쌍마다 두 답변을 **블라인드**(정체 숨김)로, **A/B 순서를 양방향**으로 강판정 모델(예: gpt-4o)이 "어느 쪽이 질의·조건에 더 적합한가" 심사한다(위치편향 상쇄). 판정을 (query_id, config_a, config_b, order, judge_model) 키로 **캐시**. 순서스왑 판정을 합쳐 무승부/승자를 정하고, **config×계층 승률 표 + 전체 순위 + 정성 예시**로 리포트한다.

## Acceptance criteria

- [ ] 각 config 쌍·쿼리를 양방향 순서로 블라인드 심사한다
- [ ] 심사 판정이 캐시되어 재실행 시 재호출하지 않는다(카운팅 검증)
- [ ] 순서스왑 합산·무승부 처리·계층별 승률 집계가 결정적(순수 함수 테스트)
- [ ] 최종 리포트(config×계층 승률 + 순위 + 정성 예시)가 생성된다

## Blocked by
- 02, 03, 04 (모든 config 답변), 05 (쿼리셋)
