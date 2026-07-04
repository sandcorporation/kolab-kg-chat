# PRD: 추천 읽기 경로를 tool-calling 에이전트에서 RAG로 전환

Status: ready-for-agent
Labels: ready-for-agent

## Problem Statement

현재 읽기 경로는 tool-calling 에이전트(langgraph StateGraph, ADR-0013)다. LLM이 도구(search_products·find_products·find_compatible·get_attributes·semantic_search·recommend)를 스스로 골라 여러 라운드 호출한 뒤 추천한다. 이 구조의 문제:

- **비결정성·과고착.** LLM이 검색을 오케스트레이션하다 보니 대화 히스토리에 과고착해 엉뚱한 재검색을 하고(예: 이전 '핀셋' 실패 검색을 새 일반 질의에도 반복), 같은 입력에도 결과가 흔들린다.
- **도구 과다 → 시스템 프롬프트 비대.** 도구가 6개라 '어떤 도구를·언제·어떻게, 재검색하지 말라'는 지침이 7섹션까지 늘었고, 유지보수·토큰이 커진다.
- **느린 첫 토큰.** 도구 루프가 ~9초 돌아 첫 근거 토큰이 늦게 나온다.

## Solution

읽기 경로를 **RAG(retrieve-then-read)** 로 바꾼다. 검색은 시스템이 **결정적으로** 수행하고, LLM은 **검색된 후보를 읽고 적합한 것을 골라 근거를 쓰는** 일만 한다(도구 호출 없음).

```
질의 → [키워드 검색 ∪ 시맨틱 검색] 합집합·중복제거 top-K(속성 포함)
     → LLM: 후보 중 적합한 것 선택 + 한국어 근거(없으면 되묻기)   ← 도구·재검색 없음
     → 그라운딩·가격 결정적 부착(ProductEnricher) → SSE
```

사용자 관점 변화: (1) 같은 질의에 일관된 결과, (2) 대화 화제 전환 시 이전 실패 검색을 반복하지 않음, (3) 첫 토큰이 빨리 나옴. SSE 계약(token·recommendation·done)과 멀티턴·가격·마크다운은 유지된다.

## User Stories

1. 연구원으로서, 같은 질문을 다시 하면 같은 추천을 받고 싶다. 신뢰할 수 있는 도구가 되도록.
2. 연구원으로서, 이전에 못 찾은 품목("핀셋")을 물은 뒤 "어떤 상품 있어?"로 화제를 바꾸면 이전 품목을 반복하지 않길 원한다. 대화가 답답하지 않도록.
3. 연구원으로서, 추천 근거가 이전보다 빨리 뜨길 원한다. 오래 기다리지 않도록.
4. 연구원으로서, 서술형("액체를 정확히 옮기는 도구")이든 정확 키워드("cryogenic vials")든 잘 찾길 원한다. 표현 방식과 무관하게.
5. 연구원으로서, 요청에 딱 맞는 상품이 없으면 억지 추천 대신 무엇을 찾는지 되물어주길 원한다. 오추천을 피하도록.
6. 연구원으로서, 추천 상품 카드에 가격·근거 속성·URL이 그대로 붙길 원한다. 판단에 필요한 정보를 위해.
7. 연구원으로서, "그 첫 번째 상품은 어디에 써?" 같은 후속 참조가 이어지길 원한다. 자연스러운 대화를 위해.
8. 개발자로서, LLM에게 도구 오케스트레이션을 시키지 않아 시스템 프롬프트가 짧고 단순하길 원한다. 유지보수·토큰 절감.
9. 개발자로서, 검색이 결정적 모듈(HybridRetriever)로 분리돼 후보 구성을 격리 테스트하고 싶다.
10. 개발자로서, LLM 선택·근거 단계(RagRecommender)를 ScriptedChatModel로 결정적으로 테스트하고 싶다.
11. 개발자로서, RAG로 교체하기 전에 기존 eval 하네스로 에이전트와 품질을 A/B 비교하고 싶다. 회귀 없이 대체하도록.
12. 운영자로서, RAG가 에이전트보다 품질이 낮으면 대체를 보류하고 싶다. config5(융합+재랭크) 실패의 교훈대로.
13. 개발자로서, 검색 top-K·후보 수·모델을 `.env`로 조절하고 싶다. 저사양·비용 튜닝.
14. 연구원으로서, 검색 중임을 알리는 짧은 상태 표시("검색 중…")를 보고 싶다. 진행 중임을 알도록.
15. 개발자로서, 긴 대화·많은 후보에도 프롬프트가 토큰 예산 내로 유지되길 원한다(ContextTrimmer 재사용). 컨텍스트 초과 방지.
16. 개발자로서, 읽기 경로가 여전히 단일(ADR-0011 정신)이길 원한다. 이중 경로 혼선 없이.
17. 연구원으로서, 도구 루프의 무한 재시도·되풀이가 사라지길 원한다. 응답이 끊기지 않도록.
18. 개발자로서, 프론트·SSE·views가 그대로이길 원한다(공개 인터페이스 유지). 변경 폭 최소화.

## Implementation Decisions

### 아키텍처 — RAG 파이프라인

- **HybridRetriever(딥모듈)**: `retrieve(query, k) → 후보[]`. 내부에서 **키워드 검색(GraphStore.search_products) ∪ 시맨틱 검색(SemanticSearch)** 을 각각 돌려 `source_id`로 **합집합·중복제거**하고 top-K(기본 15~20)를 남긴다. **cross-encoder 재랭크는 하지 않는다**(config5 실패 회피 — 리콜 위주, 정밀도는 LLM 선택이 담당). 각 후보에 이름 + 속성(get_attributes)을 붙여 LLM이 적합성을 판단할 근거를 제공한다.
- **RagRecommender(딥모듈)**: 기존 `astream(query, history)`/`run(...)` 인터페이스를 유지한다. HybridRetriever로 후보를 얻고, 후보(번호·이름·속성) + 대화 히스토리 + 질의를 **하나의 짧은 프롬프트**로 만들어 **단일 스트리밍 LLM 호출**을 한다. LLM은 적합한 후보 번호를 선언하고 한국어 근거를 쓴다. 도구 호출·재검색은 없다.
- **선택 파싱(결정적)**: 프롬프트 계약 — LLM은 **첫 줄에 기계가독 선택**(예: `선택: 2, 5, 7`, 없으면 `선택: 없음`)을 쓰고, **다음 줄부터 근거**를 쓴다. 래퍼는 첫 선택 줄을 파싱해 후보 번호 → `source_id`로 매핑하고(추천 id 포착), 그 줄은 토큰 스트림에서 **suppress**하며 이후 근거만 token 이벤트로 흘린다. `선택: 없음`이면 recommended_ids는 비고 근거(되묻기)만 스트리밍한다.
- **검색은 현재 질의로만.** 히스토리는 검색에 쓰지 않는다(결정적 → 히스토리發 재검색·과고착 버그 근본 해소). 히스토리는 프롬프트에 '이전 대화(참조용)'로만 넣어 '첫 번째 상품' 류 참조 해소·연속성에 쓴다.
- **호환 제거.** find_compatible(그래프 순회)은 제거한다. 호환 관계는 이름·설명에 인코딩돼 키워드/시맨틱이 대부분 커버한다(리트리벌 실험 증거: 호환 이점 미미).

### 프롬프트

- 도구 오케스트레이션 지침(어떤 도구·언제·재검색 금지 등)을 전부 제거하고 **2~3줄**로 축소: "아래 후보 중 사용자 요청에 맞는 상품 번호를 첫 줄 `선택:`에 쓰고, 다음 줄부터 근거를 쓰라. 맞는 게 없으면 `선택: 없음`과 되묻는 질문을 쓰라. 상품/URL/가격은 시스템이 붙이니 지어내지 말라. 이전 대화는 참조용."

### 스트리밍·상태

- `on_tool_start` 기반 status(도구별 라벨)는 사라진다. 대신 검색 시작 시 **`검색 중…` status 1회**를 방출하고 이후 근거 토큰을 흘린다. 검색이 ~1초라 **첫 토큰 지연이 크게 준다**(부수 효과). SSE 이벤트 종류(token·status·recommendation·done·error)는 그대로.
- **ContextTrimmer 재사용**: 히스토리+후보 프롬프트를 `AGENT_TOKEN_BUDGET` 내로 트림.

### 인터페이스·재사용·제거

- **유지(공개)**: `RecommendationAgent`가 노출하던 `astream/run` 인터페이스 계약 → RagRecommender가 동일 시그니처로 대체. `streaming.py`·`views`·프론트·SSE 계약 불변. `ProductEnricher`(가격·그라운딩)·`HistorySerializer`·`ContextTrimmer`·`GraphStore.search_products`/`get_attributes`·`SemanticSearch` 재사용.
- **제거**: langgraph StateGraph, GraphTools의 도구 래퍼(find_products·find_compatible·get_attributes·search_products·semantic_search·recommend as tools)와 `Command`/`ToolNode` 경로, `TOOL_STATUS_LABELS`, 7섹션 도구 프롬프트. (GraphStore의 조회 메서드 자체는 검색에 계속 쓰인다.)

### 검증·이행 (A/B 게이트)

- eval 하네스(`apps/eval`, 250 코퍼스·31 질의·LLM 심사)를 eval 브랜치에서 복원하고 **RAG config를 추가**한다. config5(HybridReranker)와 달리 RAG는 재랭크가 아니라 **LLM 읽기·선택**이므로 새 config로 둔다.
- 기준선 config4(에이전트+embeddings, 실험 최고 2.42)와 RAG를 **절대 적합도·승률·지연**으로 A/B한다.
- **RAG ≥ 에이전트일 때만** 에이전트/StateGraph를 제거하고 RAG를 단일 읽기 경로로 확정한다. 미달이면 검색을 개선하거나 대체를 보류한다(결정 기록은 ADR).

### API·설정

- SSE 요청/이벤트 계약 불변(`ChatIn.query/history`, `ProductCard.price_*` 유지).
- `.env`: 검색 top-K(`RAG_TOP_K`, 기본 20 등), 후보 최대(선택), 기존 `AGENT_TOKEN_BUDGET`·`AGENT_HISTORY_TURNS` 재사용.

## Testing Decisions

좋은 테스트는 공개 인터페이스로 **외부 행동**을 검증하고 구현에 결합하지 않는다. 결정적 파트는 fake/ScriptedChatModel로 테스트(기존 `test_recommendation_agent`·`test_context_trim`·counting double 패턴 계승).

- **HybridRetriever**(fake 키워드/시맨틱 제공자): 두 소스의 합집합·중복제거, top-K 절단, 후보에 이름·속성 부착. 한쪽이 비어도 다른 쪽으로 후보 산출. 결정적.
- **선택 파서**: `선택: 2, 5` → 후보→source_id 매핑; `선택: 없음` → 빈 추천; 형식 이탈 시 안전 처리(빈 추천). 결정적 단위.
- **RagRecommender**(ScriptedChatModel + fake retriever): astream이 근거 token → recommendation → done을 방출; 선택 줄은 토큰에서 suppress; `선택: 없음`이면 recommended 비고 되묻기만; 히스토리가 프롬프트에 포함(모델이 받은 메시지 검증). 검색이 현재 질의로만 수행됨(히스토리 바뀌어도 retriever 입력 동일).
- **SSE 계약**(기존 test_sse_streaming 계승): token·recommendation·done + `검색 중…` status.
- **품질 A/B**: eval 하네스로 config4(에이전트) vs RAG 절대점수·승률·지연. RAG 채택 조건의 근거.
- **Playwright 라이브**: diagnose 시나리오("핀셋있어?" → "어떤상품들있어?") 재검색 없음, 서술형·키워드 추천, 가격·멀티턴 참조, 첫 토큰 지연 단축.

## Out of Scope

- find_compatible/그래프 다중홉 추론 — 제거(키워드/시맨틱으로 대체, 실험 증거).
- cross-encoder/LLM 재랭크(config5 방식) — 하지 않음(리콜은 검색, 정밀도는 LLM 선택).
- 대화형 질의 재작성(history→standalone query rewrite) — 이번엔 안 함(검색은 현재 질의만, 참조는 생성이 처리).
- 속성 필터 파싱을 위한 별도 LLM 호출 — 시맨틱/키워드로 커버.
- 에이전트/RAG 플래그 병행 장기 운영 — A/B 후 단일 경로로 확정.
- 브라우즈 전용 역량(카테고리 목록 도구) — 별도 후속. 모호 질의는 LLM 되묻기로 처리.

## Further Notes

- 이 전환은 ADR-0007(툴콜 에이전트)·0011(단일 읽기 경로)·0013(StateGraph)을 **대체하는 새 ADR**로 남긴다(되돌리기 비용·트레이드오프 큼). 다만 **실제 제거는 eval A/B 통과 후**에만 한다 — ADR에 A/B 결과를 근거로 기록.
- config5 실패는 '재랭크' 때문이지 '하이브리드 검색' 때문이 아니다. RAG는 재랭크 대신 LLM 읽기를 쓰므로 config5의 결론이 RAG를 배제하지 않는다 — 그래서 A/B가 필요하다.
- 저사양 전제: top-K·토큰 예산 보수적 기본값, 검색 1회+생성 1회로 LLM 왕복 축소.
- eval_graph/eval_corpus는 현재 db(knowledge_graph)와 별개다. A/B 실행 시 코퍼스 재구축(build_eval_corpus·embed_corpus)이 필요할 수 있다.
