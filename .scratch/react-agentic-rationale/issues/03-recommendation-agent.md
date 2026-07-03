# 03 — RecommendationAgent (langgraph tool-calling)

Status: done — `apps/agent/recommendation_agent.py` (langgraph create_react_agent), 테스트 `tests/test_recommendation_agent.py` 통과.

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

langgraph tool-calling 에이전트. 질의를 받아 도구(02)로 조건 판단·검색·(호환 순회)를 자율 수행하고 `recommend(ids)`로 최종 상품을 명시 선택한 뒤, **검색된 상품·속성에만 근거한 추천 근거 프로즈를 스트리밍**한다. **반복 상한 5**회 후 강제 종료. 모호하면 clarification, 0건이면 제약 완화(각 1회)를 에이전트가 판단. LLM = langchain-openai ChatOpenAI(스트리밍·tool-calling, `OPEN_AI_KEY`); 테스트는 fake chat model.

## Acceptance criteria

- [ ] 에이전트가 도구를 호출해 상품을 검색하고 recommend(ids)로 최종 선택
- [ ] 근거 프로즈가 선택된 상품·속성에 근거(환각 없음)
- [ ] 도구 호출이 상한(5) 내로 제한됨
- [ ] 모호 질의 → clarification, 0건 → 완화(각 1회)
- [ ] fake chat model + 목 도구로 tool-calling 흐름·최종픽·근거를 결정적 검증(prior art: fake_llm, test_agent_flow)

## Blocked by
- `02-agent-tools.md`
