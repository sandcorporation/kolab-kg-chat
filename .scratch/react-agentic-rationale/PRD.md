# PRD — React 프론트 + LLM 에이전트 추천 근거·상품 URL

Status: ready-for-agent

## Problem Statement

(1) 현재 프론트는 Django가 서빙하는 **바닐라 HTML 위젯** 한 장이라, 유지보수·확장이 어렵고 제대로 된 컴포넌트 기반 UI가 아니다. (2) 추천 응답은 정형 grounding 칩 + "요구조건에 맞는 상품 N건" 같은 **정형 요약**만 보여줄 뿐, *왜 이 상품이 이 실험/용도에 맞는지*를 사람이 읽을 **LLM 생성 근거**가 없고, 상품으로 바로 갈 **클릭 가능한 kolab 링크**도 없다.

## Solution

프론트를 **React(Vite+TypeScript+Orval)** 로 교체해 nginx 단일 엔드포인트 뒤에서 서빙한다. 읽기 경로를 **langgraph tool-calling 에이전트**로 바꿔, 에이전트가 지식그래프를 도구로 탐색해 상품을 고르고(`recommend(ids)`), **검색 결과에만 근거한 추천 근거를 실시간 토큰으로 스트리밍**한다. 각 추천 상품에는 시스템이 **결정적 kolab URL + 썸네일 + grounding**을 부착한다. 사용자는 실시간 근거 프로즈를 읽고, 카드의 링크로 상품 페이지로 이동한다.

## User Stories

1. 사용자로서, 나는 챗에서 "왜 이 상품을 추천하는지" LLM이 쓴 근거를 실시간으로 읽고 싶다.
2. 사용자로서, 나는 추천 근거가 실제 검색된 상품·속성에 기반하길(환각 없음) 바란다.
3. 사용자로서, 나는 추천 카드의 링크를 눌러 kolabshop 상품 페이지로 바로 가고 싶다.
4. 사용자로서, 나는 카드에서 상품명·썸네일 이미지·근거 속성(grounding)을 함께 보고 싶다.
5. 사용자로서, 나는 "이 장비와 호환되는 것"처럼 관계 기반 질문에도 답을 받고 싶다(에이전트 다홉 호환 순회).
6. 사용자로서, 나는 모호하게 물으면 1회 되묻기를, 0건이면 완화된 대안을 받고 싶다.
7. 사용자로서, 나는 근거가 토큰 단위로 실시간 흐르는 반응형 챗을 원한다.
8. 프론트 개발자로서, 나는 React 컴포넌트로 UI를 구성하고 Vite로 개발/빌드하고 싶다.
9. 프론트 개발자로서, 나는 Orval로 OpenAPI에서 타입(추천 페이로드 등)을 생성해 타입 안전하게 쓰고 싶다.
10. 프론트 개발자로서, 나는 SSE `/chat` 스트림을 이벤트 타입(token/recommendation/clarification/done/error)별로 분기해 렌더하고 싶다.
11. 운영자로서, 나는 프론트+백엔드가 nginx 단일 엔드포인트(:80)로 배포되길 바란다(React dist 서빙 + api 프록시).
12. 백엔드 개발자로서, 나는 에이전트가 그래프 도구(속성검색·호환순회·속성조회)만으로 추론하고 최종 상품을 명시 선택(`recommend(ids)`)하길 바란다.
13. 백엔드 개발자로서, 나는 상품 URL을 LLM이 아니라 **시스템이 it_id로 결정적 생성**해(환각 차단) 부착하길 바란다.
14. 백엔드 개발자로서, 나는 에이전트 반복이 상한(5)으로 묶여 비용·지연이 폭주하지 않길 바란다.
15. 백엔드 개발자로서, 나는 에이전트를 fake chat model로 결정적으로 테스트하고 싶다.

## Implementation Decisions

- **읽기 경로 = langgraph tool-calling 에이전트** (ADR-0007 혼합 에이전트 실체화). 도구: `find_products(conditions)`(GraphStore 속성필터) · `find_compatible(product_id, depth)`(AGE 다홉) · `get_attributes(product_id)` · `recommend(ids)`(최종 선택). **반복 상한 5**회 후 강제 종료·근거 생성.
- **근거(rationale)** = 검색된 상품·속성에만 근거한 **전체 프로즈**를 `astream_events`로 **실시간 토큰 스트리밍**(ADR-0001 grounding, 환각 금지). 상품·URL은 LLM이 만들지 않는다.
- **결정적 부착(ProductEnricher)**: 에이전트가 고른 id에 `url = https://www.kolabshop.com/shop/item.php?it_id={source_id}`, `image_url`(정규화된 it_img1), `grounding`(그래프 속성)을 시스템이 붙인다.
- **되묻기(모호)·완화(0건)** 는 에이전트 판단으로 흡수하되 `clarification` 이벤트는 유지, 1회 제한.
- **SSE 계약**:
  - `token` : LLM 근거 프로즈 델타
  - `recommendation` : `{ products: [{ source_id, name, url, image_url, grounding: [{name, value, provenance}] }] }`
  - `clarification` / `done` / `error`
- **LLM**: langchain-openai `ChatOpenAI`(스트리밍·tool-calling), env `OPEN_AI_KEY`/`OPENAI_MODEL`. 테스트는 fake chat model. deps: `langgraph`, `langchain-openai`.
- **프론트**: **Vite + React + TypeScript + Orval**(OpenAPI→타입; SSE 이벤트 페이로드 스키마를 Django Ninja OpenAPI components에 정의해 타입 생성, SSE 소비는 수제 fetch+ReadableStream 리더). 기존 바닐라 위젯 대체.
- **배포**: nginx **멀티스테이지**(node 빌드 → dist) 로 React를 `/`에서 서빙, `/chat`·`/recommend`·`/health`·`/openapi.json`은 api 프록시. **단일 엔드포인트(:80)** 유지, SSE 버퍼링 off(ADR-0007).
- **OpenAPI**: `recommendation` 등 SSE 이벤트 페이로드를 Ninja Schema로 정의해 OpenAPI에 노출(Orval 타입 생성용).

## Testing Decisions

좋은 테스트는 외부 행동만 검증한다. LLM은 결정적 fake chat model로 대체한다.

- **Agent Tools**: 실제 GraphStore(AGE 컨테이너) 대상 `find_products`/`find_compatible`/`get_attributes`/`recommend` 결과 검증(결정적). prior art: `test_graph_store`, `test_compatibility`.
- **RecommendationAgent**: **fake chat model + 목 도구**로 tool-calling 흐름 → `recommend(ids)` 최종 픽 → 근거 스트리밍(이벤트 시퀀스) 검증. 반복 상한 준수. prior art: `fake_llm`, `test_agent_flow`.
- **ProductEnricher**: id → url/image_url/grounding 결정적 부착 단위 테스트.
- **SSE 스트림**: fake agent 주입 → token/recommendation/clarification/done 시퀀스 + recommendation 페이로드(url 포함) 검증. prior art: `test_sse_streaming`.
- **프론트**: **Playwright E2E**(단일 엔드포인트 실브라우저 — 스트리밍 근거·카드·링크·되묻기) + 핵심 컴포넌트 vitest 렌더 1~2개. prior art: 기존 Playwright 위젯 테스트, embed-chat 위젯 테스트.

## Out of Scope

- pgvector 유사도 검색(ADR-0009 보류) — 에이전트 도구에서 제외.
- 비전/이미지 스펙 추출(별도 PRD, vision-spec-extraction).
- 멀티테넌트·HITL.
- 에이전트 장기 메모리/체크포인터 영속화(인라인 실행, ADR-0007).
- Orval의 SSE 스트림 클라이언트 생성(불가 — SSE는 수제 리더).
- 대화 히스토리 서버 저장(단일 페이지 세션 내 유지로 충분).

## Further Notes

- langgraph를 실제로 도입하는 첫 지점(그동안 읽기 경로는 수제 파이프라인이었음). 호환 도구가 활성화돼 그래프의 관계 추론이 비로소 가치를 낸다.
- 상품 URL 형식: `https://www.kolabshop.com/shop/item.php?it_id={it_id}` (실물 확인됨).
- 키 없는 데모(HeuristicParser)는 이제 근거를 못 만든다 — 읽기 경로는 LLM 필수(키는 .env). 자동 테스트는 fake chat model로 무키 실행.
- 프론트는 기존 위젯과 동일 기능(스트리밍 근거·카드·되묻기) + URL 링크·썸네일 추가.
