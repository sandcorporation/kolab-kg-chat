# 읽기 경로는 tool-calling 에이전트로 단일화한다

읽기 경로가 이중이었다: (1) Recommendation Agent(langgraph, `/chat`, SSE 스트리밍), (2) 구 parse→retrieve→compose 파이프라인(`/recommend`, 비스트리밍 + `flow`의 되묻기/제약완화 휴리스틱). 둘은 같은 목적(적합성 추천)을 다르게 구현해 중복·혼선을 낳았다.

## 결정

- 읽기 경로를 **Recommendation Agent로 단일화**한다. 에이전트가 그래프 도구(`search_products`·`find_products`·`find_compatible`·`get_attributes`)로 근거를 모으고 `recommend(ids)`로 선택을 선언한 뒤 Rationale을 스트리밍한다.
- 구 파이프라인 일체를 **제거**한다: `pipeline`·`flow`·`Retriever`·`RecommendationComposer`·`RequirementParser`·`HeuristicParser`·`demo`, 비스트리밍 `/recommend` 엔드포인트, 레거시 위젯(`widget.html`·`/widget`).
- 키 없는 데모/E2E는 파이프라인이 아니라 **AGENT_FAKE 스크립트 에이전트**(결정적 스텁)로 충족한다.

## 이유

- **설명가능성은 그대로.** 에이전트 경로도 ADR-0001의 원칙(그래프 속성 근거)을 지킨다 — Rationale로 근거를 서술하고 시스템이 Grounding을 결정적으로 붙인다. 같은 목적의 두 구현을 유지할 이유가 없다.
- **되묻기·완화가 자연스러워진다.** `flow`의 하드코딩된 1회 되묻기/제약완화 휴리스틱을 에이전트의 판단(추가 검색·되묻기)이 대체한다.
- **자연어 매칭이 낫다.** 구 파이프라인은 통제 어휘 조건 파싱에 의존했으나, 에이전트는 `search_products`로 상품명 키워드(한/영)를 직접 매칭해 실제 질의를 더 잘 회수한다("유리 플라스크"→메스플라스크).
- 중복 코드·엔드포인트·테스트의 유지비를 제거한다.

## 결과

- **비스트리밍 JSON 추천 API를 상실**한다. 프로그램적 통합이 필요하면 다시 만들되, 그때는 에이전트를 감싸는 얇은 어댑터로 한다(파이프라인 부활이 아니다).
- 모든 추천이 LLM 호출을 수반한다 — 키·비용이 전제이고, 데모는 AGENT_FAKE로 우회한다.
- `/chat` SSE(ADR-0007)가 유일한 추천 경로다. OpenAPI는 SSE 페이로드 스키마만 문서화한다(코드젠용).
- 되돌리기 비용이 있어 ADR로 남긴다.
