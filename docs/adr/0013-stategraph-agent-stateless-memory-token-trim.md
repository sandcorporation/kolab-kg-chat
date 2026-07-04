# 에이전트를 커스텀 StateGraph로 짜고, 무상태 히스토리 메모리 + 토큰 예산 트리밍을 둔다

> **대체됨(Superseded by [ADR-0014](0014-rag-read-path-replaces-tool-calling-agent.md)).** tool-calling 에이전트를 RAG(retrieve-then-read)로 교체했다(A/B에서 RAG ≥ 에이전트). 무상태 히스토리·토큰 트리밍 결정은 RAG에서도 유지된다. 이 문서는 이력 보존용이다.

Recommendation Agent(ADR-0007·0011)는 `langgraph.prebuilt.create_react_agent`를 얇게 감싸 썼다. 이 prebuilt는 **deprecated**(langgraph V2에서 제거 예정)이고, (a) 멀티턴 대화 메모리가 없어 후속 질의를 이해하지 못했으며, (b) 컨텍스트 길이 방어가 recursion_limit·도구출력 상한뿐이라 토큰 단위 가드가 없었고, (c) 추천 id를 `GraphTools.recommended` 공유 뮤터블로 포착해 동시 요청에 교차오염 위험이 있었다.

## 결정

- **에이전트를 직접 짠 langgraph `StateGraph`(노드+엣지)로 교체**한다: `START → prepare → agent ⇄ tools → END`. 의존성은 이미 있는 `langgraph`(StateGraph·ToolNode·Command) + `langchain-core`(messages·trim_messages) + `langchain-openai`(ChatOpenAI). 최상위 `langchain` 패키지·v1 `create_agent` 미들웨어는 도입하지 않는다.
- **추천 포착은 그래프 state**로 옮긴다. `recommend` 도구가 `Command(update={"recommended_ids": ...})`로 state를 갱신하고 래퍼는 최종 state에서 읽는다 → 공유 사이드채널 제거(요청별 격리).
- **멀티턴 메모리는 무상태 클라이언트 히스토리**로 한다. 서버는 세션을 저장하지 않고, 프론트가 최근 N턴(`AGENT_HISTORY_TURNS`)을 요청에 담아 보낸다. 봇 턴은 라시오날레 + 추천 상품(이름·가격) 요약으로 압축한다.
- **컨텍스트 길이 방어는 토큰 예산 트리밍**으로 한다. `agent` 노드가 매 모델 호출 직전 `trim_messages`로 시스템 프롬프트 유지 + 최근 우선, `AGENT_TOKEN_BUDGET` 내로 줄인다(멀티턴 + 턴 내 도구출력 누적 둘 다 방어).

`RecommendationAgent.astream/run` 공개 인터페이스와 SSE 계약(token·status·recommendation·done)은 그대로다 — `astream_events(v2)`를 유지하므로 진행 상태줄·마크다운도 호환된다(ADR-0011 단일 읽기 경로 내부 구현 교체).

## 이유

- **미래 대응.** deprecated prebuilt 제거에 앞서 우리가 통제하는 그래프로 옮긴다. 노드·엣지가 명시적이라 메모리·트리밍 같은 관심사를 1급으로 붙일 수 있다.
- **무상태 우선.** 저사양(2GB) 인스턴스·다중 워커·재시작을 고려하면 서버측 세션 저장(checkpointer/Postgres)보다 클라이언트 히스토리가 단순·견고하다. 프론트가 이미 대화를 표시용으로 보유한다.
- **비용·지연.** 요약(summarization) 대신 토큰 예산 트리밍을 택해 매 턴 추가 LLM 호출을 피한다.
- **동시성 안전.** 추천 포착이 요청별 state라 캐시된 단일 에이전트에서도 교차오염이 없다.

## 대안 (기각)

- `langchain.agents.create_agent`(v1) + 미들웨어: 최상위 패키지 추가·블랙박스. 노드+엣지 가시성/제어를 원해 기각.
- checkpointer(MemorySaver/Postgres) 서버 세션: 인프라·스레드 관리 추가. 무상태로 충분.
- 요약 기반 압축: 비용·지연으로 저사양 박스에 부적합.

## 결과

- 요청 스키마에 `history`가 추가된다(하위호환, 기본 빈 배열). SSE 계약 불변.
- `.env`: `AGENT_TOKEN_BUDGET`(기본 6000), `AGENT_HISTORY_TURNS`(기본 5).
- 후속 질의("첫 번째 상품…")가 이어지고, 긴 대화·큰 도구출력에도 컨텍스트가 예산으로 바운드된다.
