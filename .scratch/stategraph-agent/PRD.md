# PRD: Agent를 노드+엣지 StateGraph로 마이그레이션 (+ 멀티턴 메모리 · 컨텍스트 방어 · 가격 노출)

Status: ready-for-agent
Labels: ready-for-agent

## Problem Statement

현재 Recommendation Agent는 이미 langgraph 기반이지만, **deprecated된 `langgraph.prebuilt.create_react_agent`** 를 얇게 감싸 쓰고 있다(langgraph V2에서 제거 예정). 게다가:

- **멀티턴 대화 메모리가 없다.** 매 턴이 무상태라 "아까 첫 번째 상품 스펙 알려줘" 같은 후속 질의를 이해하지 못한다.
- **컨텍스트 길이 방어가 암묵적**이다. 루프 상한(recursion_limit)과 도구 출력 상한만 있고, 토큰 예산 트리밍·윈도잉이 없다.
- 추천 id를 `GraphTools.recommended`라는 **공유 뮤터블 사이드채널**로 포착해, 에이전트가 startup에 1개만 캐시되는 구조상 **동시 요청 시 서로의 추천을 덮어쓰는 잠재 레이스**가 있다.
- 추천 카드에 **가격이 없다.** 가격 데이터는 변형(Variant)에 존재하나 상품 카드·대화에 노출되지 않는다.

## Solution

Recommendation Agent를 **직접 짠 langgraph `StateGraph`(노드+엣지)** 로 마이그레이션한다. 그래프에 컨텍스트 관리와 추천 포착을 1급으로 녹이고, 무상태 멀티턴 메모리와 가격 노출을 더한다.

- **노드+엣지 그래프**: `START → prepare → agent ⇄ tools → END`. deprecated prebuilt를 걷어내고, 이미 설치된 `langgraph`(StateGraph·ToolNode) + `langchain-core`(messages) + `langchain-openai`(ChatOpenAI)만 쓴다(최상위 `langchain` 패키지 불필요).
- **멀티턴 메모리(무상태)**: 클라이언트가 최근 N턴 대화를 요청에 담아 보내고(서버 무상태), `prepare` 노드가 이를 메시지로 병합한다.
- **컨텍스트 방어**: `agent` 노드가 매 모델 호출 직전 토큰 예산으로 메시지를 트림한다(멀티턴 누적 + 턴 내 도구출력 누적 둘 다 방어).
- **추천 포착**: `recommend` 도구가 그래프 state를 갱신(Command)해 요청별로 격리한다(사이드채널 레이스 제거).
- **가격 노출**: 엔리처가 변형 가격을 집계해 상품 카드·대화 히스토리에 가격 범위("₩12,000~₩45,000")를 표기한다.

사용자에게 보이는 변화: (1) 후속 질의가 이어진다, (2) 상품 카드/대화에 가격이 보인다, (3) 긴 대화·큰 도구출력에도 안정적이다.

## User Stories

1. 연구원으로서, 이전 추천을 이어 "그 중 첫 번째 상품 스펙 알려줘"라고 물으면 에이전트가 맥락을 이해하길 원한다. 매번 처음부터 설명하지 않기 위해.
2. 연구원으로서, "아까 그거보다 더 저렴한 걸로"처럼 직전 추천을 기준으로 후속 요청을 하고 싶다. 자연스러운 대화를 위해.
3. 연구원으로서, 추천 상품 카드에서 가격 범위를 보고 싶다. 예산에 맞는지 즉시 판단하기 위해.
4. 연구원으로서, 대화 히스토리 요약에도 이전 추천 상품의 이름과 가격이 남길 원한다. 후속 지시("두 번째 거")가 정확히 해소되기 위해.
5. 연구원으로서, 아주 긴 대화를 이어가도 응답이 끊기거나 느려지지 않길 원한다. 컨텍스트 초과로 실패하지 않기 위해.
6. 운영자로서, 여러 사용자가 동시에 질문해도 추천 결과가 서로 섞이지 않길 원한다. 신뢰할 수 있는 서비스를 위해.
7. 운영자로서, 대화 히스토리 길이·토큰 예산을 `.env`로 조절하고 싶다. 저사양 인스턴스 비용·지연을 관리하기 위해.
8. 운영자로서, 에이전트가 deprecated API에 의존하지 않길 원한다. 라이브러리 업그레이드(langgraph V2)에 깨지지 않기 위해.
9. 개발자로서, 에이전트가 명시적 노드+엣지 그래프이길 원한다. 흐름을 눈으로 보고 확장(노드 추가)하기 쉽게.
10. 개발자로서, 추천 포착이 공유 뮤터블이 아니라 그래프 state이길 원한다. 동시성 버그 없이 테스트 가능하도록.
11. 개발자로서, 컨텍스트 트리밍이 독립 모듈이길 원한다. 예산 경계 동작을 결정적으로 테스트하기 위해.
12. 개발자로서, 기존 SSE 계약(token·status·recommendation·done 이벤트)이 그대로 유지되길 원한다. 프론트·스트리밍 코드 변경을 최소화하기 위해.
13. 연구원으로서, 후속 질의 중에도 진행 상태줄(도구 호출)과 마크다운 근거가 이전처럼 보이길 원한다. 일관된 경험을 위해.
14. 연구원으로서, 가격 정보가 없는 상품은 억지 숫자 대신 자연스럽게 생략되길 원한다. 오정보를 피하기 위해.
15. 개발자로서, 프론트가 표시용으로 갖고 있는 대화 turns에서 히스토리를 직렬화해 보내길 원한다. 서버에 세션 저장소를 두지 않기 위해.
16. 운영자로서, 첫 배포/재시작·다중 워커에서도 메모리 동작이 일관되길 원한다(무상태라 서버 재시작에 안전).
17. 개발자로서, ScriptedChatModel로 그래프 루프·트리밍·추천 state·가격 집계를 결정적으로 테스트하고 싶다.
18. 연구원으로서, 멀티턴 대화와 가격 표시가 실제 브라우저에서 동작함을 확인하고 싶다(Playwright 라이브).

## Implementation Decisions

### 아키텍처 — 커스텀 StateGraph (노드+엣지)

- deprecated `langgraph.prebuilt.create_react_agent`를 걷어내고 **직접 `StateGraph`를 구성**한다. 의존성은 이미 설치된 `langgraph`(StateGraph·ToolNode·Command) + `langchain-core`(messages·trim_messages) + `langchain-openai`(ChatOpenAI). 최상위 `langchain` 패키지는 추가하지 않는다.
- 그래프 토폴로지(프로토타입으로 확정한 형태):

  ```
  START → prepare → agent ⇄ tools → END
    - prepare: 입력 history(+현재 질의)를 state.messages로 병합
    - agent:   messages를 토큰 예산으로 trim → 시스템 프롬프트 + 도구 바인딩 모델 호출
    - 조건부 엣지: 마지막 AIMessage에 tool_calls 있으면 → tools, 없으면 → END
    - tools:   ToolNode(그래프 도구들). recommend는 Command로 state 갱신
  ```

- **State 스키마**: `messages`(append-reducer) + `recommended_ids: list[str]`. `history`는 그래프 입력으로 받아 prepare에서 소비.
- **공개 인터페이스 유지**: `RecommendationAgent.astream(query, history=...)` / `run(...)`는 그대로 두고 내부만 컴파일된 StateGraph로 교체한다. 래퍼의 `astream`은 컴파일 그래프의 `astream_events(v2)`로 `on_tool_start`(status)·`on_chat_model_stream`(token)을 계속 방출하고, 그래프 최종 state에서 `recommended_ids`를 읽는다. → `streaming.py`·views·status/token/마크다운은 변경 없음(ADR-0011 단일 읽기 경로 유지).

### 멀티턴 메모리 (무상태 · 클라이언트 히스토리)

- 요청 스키마 `ChatIn`에 `history: list[{role, content}]`를 추가한다(기본 빈 리스트 → 하위호환). `role`은 user|assistant.
- 프론트는 표시용 `turns`에서 최근 N턴을 직렬화해 보낸다. 봇 턴은 **라시오날레 텍스트 + 추천 상품 요약 한 줄**(상품명 + 가격 범위)로 압축한다(카드 전체·grounding은 제외).
- `prepare` 노드가 history를 Human/AI 메시지로 변환해 현재 질의 앞에 놓는다.
- 히스토리 턴 수 상한은 `.env`로 제어(`AGENT_HISTORY_TURNS`).

### 컨텍스트 길이 방어 (토큰 예산 트리밍)

- `agent` 노드가 매 모델 호출 직전 `langchain_core.messages.trim_messages`로 트림한다: 시스템 프롬프트는 항상 유지(`include_system`), 최근 메시지 우선, 토큰 예산 내로. 이로써 멀티턴 누적과 턴 내 도구출력 누적을 모두 방어한다.
- 토큰 예산은 `.env`로 제어(`AGENT_TOKEN_BUDGET`). 카운팅은 운영에선 모델 토크나이저, 테스트에선 결정적 카운터(예: 메시지 수/문자 길이 기반)를 주입해 경계 동작을 검증한다.
- 기존 `recursion_limit`(루프 상한)은 유지한다.

### 추천 포착 (그래프 state + Command)

- `recommend` 도구가 `Command(update={"recommended_ids": ids})`를 반환해 state를 갱신한다. ToolNode가 이를 적용한다.
- `GraphTools.recommended` 공유 뮤터블 사이드채널을 **제거**한다 → 추천 포착이 요청별 state로 격리되어 동시 요청 레이스가 사라진다.
- 래퍼는 그래프 실행 후 최종 state의 `recommended_ids`를 enricher에 넘긴다.

### 가격 노출

- **가격 집계기(딥모듈)**: 그래프 store에 상품의 변형 가격에서 최저·최고를 구하는 조회를 추가한다(`HAS_VARIANT` 가격 집계, `price IS NOT NULL`만). 반환은 `(min, max)` 또는 둘 다 없으면 `(None, None)`.
- `ProductCard` 스키마에 `price_min: int | None`, `price_max: int | None`를 추가한다. 엔리처가 카드에 채운다.
- 표기: 프론트 카드·대화 히스토리에서 `min==max`면 단일가, 아니면 범위 "₩12,000~₩45,000". 가격이 없으면(둘 다 None) 가격 줄을 생략한다(억지 표기·오정보 금지, ADR-0001 결정적 부착 원칙과 정합).
- 통화·천단위 포맷은 프론트 표시 계층에서 처리(KRW).

### API 계약 변화

- `POST /chat` 요청: `{ query: str, history?: [{role, content}] }` (history 선택, 기본 빈 배열).
- SSE 이벤트: 변화 없음(token·status·recommendation·done·error). `recommendation`의 `products[]` 카드에 `price_min`/`price_max` 추가(하위호환, 기존 필드 유지).
- Orval 코드젠 재생성으로 프론트 타입(ChatIn.history, ProductCard.price\_\*) 반영.

### 모듈 (딥모듈 우선)

빌드/수정할 모듈:

- **AgentGraph 빌더**(신규, 딥): 노드·엣지·state 스키마를 조립해 컴파일된 그래프를 반환. 복잡한 그래프 배선을 단순 인터페이스 뒤로.
- **ContextTrimmer**(신규, 딥·소형): 토큰 예산 + 시스템 유지 트리밍. 카운터 주입으로 결정적 테스트.
- **HistorySerializer**(신규): 클라 `turns` → `history` 페이로드(봇 턴은 라시오날레+추천 요약) 직렬화(프론트) 및 서버측 history→messages 변환(prepare).
- **PriceRange 집계기**(신규): store 변형가 최저·최고 조회 + 엔리처 통합.
- **RecommendationAgent 래퍼**(수정): astream/run 유지, 내부를 StateGraph로 교체, history 입력·recommended_ids를 state에서 수신.
- 수정: `schemas`(ChatIn.history, ProductCard.price\_\*), `views`(history 전달), `runtime`(그래프 조립), `tools`(recommend→Command, 사이드채널 제거), `enricher`(가격), `graph/store`(가격 조회), 프론트(`sse.ts`·`App.tsx`: 히스토리 전송·가격 표시), `.env(.example)`·README.

## Testing Decisions

좋은 테스트는 **외부 행동을 공개 인터페이스로** 검증하고 내부 구현에 결합하지 않는다. 결정적 파트는 fake로 테스트한다(기존 `ScriptedChatModel`·counting double 패턴 계승).

- **AgentGraph / RecommendationAgent**(ScriptedChatModel): 도구 루프가 돌고 최종 rationale·recommended_ids를 낸다; `on_tool_start`→status·token 이벤트가 그대로 방출된다; 도구 없는 질의는 즉시 응답. 기존 `test_recommendation_agent.py`·`test_semantic_tool.py` 계승.
- **추천 포착(state/Command)**: recommend 호출이 그래프 state의 recommended_ids를 갱신하고, 사이드채널 없이 래퍼가 이를 읽는다. 서로 다른 두 실행이 격리됨(레이스 없음).
- **ContextTrimmer**: 예산 초과 시 시스템 프롬프트는 유지하고 오래된 메시지부터 제거; 예산 내면 그대로. 결정적 카운터 주입.
- **멀티턴 메모리**: history가 주어지면 prepare가 메시지로 병합하고 모델이 이전 맥락을 본다(스크립트 모델이 받은 messages 검증). history 없으면 단일턴 회귀 없음.
- **PriceRange 집계기**: 변형 여러 개면 (min,max); 가격 없는 변형 제외; 전부 없으면 (None,None). 엔리처 카드에 price_min/max가 붙고 없으면 생략.
- **SSE 계약**(기존 `test_sse_streaming.py`): recommendation 카드에 price 필드 포함, status/token/done 유지.
- **Playwright 멀티턴 라이브**: 로컬 스택에서 1) 추천 → 2) "첫 번째 상품 스펙" 후속 이해, 3) 카드 가격 범위 표시, 4) 진행 상태줄·마크다운 유지 확인.

## Out of Scope

- 서버측 대화 영속(checkpointer/Postgres 세션) — 무상태 클라이언트 히스토리로 대체.
- 요약 기반 컨텍스트 압축(summarization) — 토큰 예산 트리밍으로 대체(비용·지연 회피).
- 최상위 `langchain` 패키지 도입 및 `create_agent`(v1) 미들웨어 — 커스텀 StateGraph로 대체.
- 가격 정렬/필터, 할인·정가 구분, 통화 변환 — 표기(범위)만. 정렬/필터는 후속.
- 세금·배송비 등 최종가 계산.
- Vision/이미지 근거 재도입(ADR-0010/0012 범위 밖).

## Further Notes

- 이 마이그레이션은 ADR-0007(툴콜 에이전트)·ADR-0011(단일 읽기 경로)의 결정 안에서 내부 구현을 교체하는 성격이다. 다만 (a) prebuilt→커스텀 StateGraph 전환, (b) 무상태 클라이언트-히스토리 메모리 모델, (c) 토큰 예산 트리밍은 되돌리기 비용이 있는 결정이므로 **짧은 ADR 1건**으로 남긴다.
- 스트리밍은 `astream_events(v2)`를 유지하므로 방금 추가한 status(진행 상태줄)·마크다운 렌더러와 그대로 호환된다.
- ScriptedChatModel은 `bind_tools`(무시)·`_agenerate`를 지원하며 `_astream`이 없어, 래퍼 astream의 "스트림 미지원 시 rationale 단어 단위 폴백"이 계속 동작한다(테스트 결정성 유지).
- 저사양(2GB/1vCPU) 전제: 토큰 예산·히스토리 턴 수 기본값은 보수적으로(예: 예산 수천 토큰, 히스토리 3~5턴) 잡고 `.env`로 조절.
