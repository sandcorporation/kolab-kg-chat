# 01 — 하네스 골격 + config 2(structured) 실행(캐시)

Status: done — EvalRunner(캐시+버전 무효화) · RetrievalConfig provenance 게이팅 · build_eval_context. config2 라이브 검증(eval_graph 추천+캐시 히트). 테스트 test_eval_runner/test_retrieval_config.

## Parent
`.scratch/retrieval-quality-eval/PRD.md`

## What to build

평가 하네스 전 구간을 가장 단순한 config로 관통하는 tracer bullet. **RetrievalConfig**(config_id → 도구 집합 + 허용 provenance)로 AgentContext를 구성하고, **EvalRunner**가 (config_id, query_id, agent_version) 키로 에이전트 답변(rationale + 추천 id + grounding)을 캐시한다. config 2 = 그래프 도구 + provenance={structured}. 같은 셀을 재실행하면 LLM을 다시 호출하지 않는다.

## Acceptance criteria

- [ ] config 2가 코퍼스 위에서 한 쿼리에 대해 추천(rationale + 상품 id)을 낸다
- [ ] provenance 필터가 config 2에서 structured 속성만 노출(llm_ocr 숨김)
- [ ] EvalRunner가 답변을 캐시하고, 재실행 시 캐시 히트(LLM 재호출 0회 — 카운팅 더블로 검증)
- [ ] 캐시 키에 agent_version 포함(버전 변경 시 무효화)

## Blocked by
- 00 (실 데이터 + 코퍼스)
