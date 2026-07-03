# 이슈 01: StateGraph 마이그레이션 트레이서 (에이전트 코어)

Status: done — 커스텀 StateGraph, recommend→Command state, 사이드채널 제거, 인터페이스·status·token 유지. 라이브 검증. 동시성 격리 테스트.
Type: AFK
Parent: .scratch/stategraph-agent/PRD.md

## What to build

`RecommendationAgent` 내부를 deprecated `create_react_agent`에서 **직접 짠 langgraph `StateGraph`(노드+엣지)** 로 교체하는 end-to-end 트레이서. 토폴로지 `START → prepare → agent ⇄ tools → END`(이 단계의 prepare는 현재 질의만 넣는 통과 노드, 트림·히스토리는 후속 이슈). `recommend` 도구는 `Command(update={"recommended_ids": ...})`로 그래프 state를 갱신하고, `GraphTools.recommended` 공유 사이드채널은 제거한다. `astream/run` 공개 인터페이스와 status·token 이벤트(astream_events)는 그대로 유지하며, 래퍼는 그래프 최종 state에서 `recommended_ids`를 읽는다.

## Acceptance criteria

- [ ] `create_react_agent` 의존 제거, 커스텀 StateGraph로 컴파일된 에이전트로 대체
- [ ] `recommend` 호출이 그래프 state의 `recommended_ids`를 갱신(Command), 사이드채널 제거
- [ ] `RecommendationAgent.astream(query)`가 여전히 token·status·result 이벤트를 방출(on_tool_start→status)
- [ ] 서로 다른 두 실행이 추천 결과를 공유하지 않음(요청별 격리 = 레이스 없음)
- [ ] 기존 테스트(test_recommendation_agent·test_semantic_tool·test_sse_streaming) 통과 + 신규 state-격리 테스트
- [ ] 로컬/prod 스택에서 추천 질의가 이전과 동일하게 동작(status·마크다운·카드)

## Blocked by

None - can start immediately
