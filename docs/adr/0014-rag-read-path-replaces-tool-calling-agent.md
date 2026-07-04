# 읽기 경로를 tool-calling 에이전트에서 RAG로 교체한다

읽기 경로는 tool-calling 에이전트였다(ADR-0007·0011·0013). LLM이 도구(search/find/compatible/attributes/semantic/recommend)를 스스로 골라 여러 라운드 호출한 뒤 추천했다. 문제: (a) 비결정성·대화 히스토리 과고착(이전 실패 검색을 새 질의에도 반복), (b) 도구 6개라 시스템 프롬프트가 7섹션까지 비대, (c) 도구 루프가 ~9초 돌아 첫 토큰이 늦음.

## 결정

읽기 경로를 **RAG(retrieve-then-read)** 로 교체한다. 검색은 시스템이 결정적으로 하고 LLM은 후보를 읽고 고르는 일만 한다(도구 호출·재검색 없음).

```
질의 → QueryAnalyzer(질의 이해, 한/영 키워드+시맨틱 질의)
     → HybridRetriever(키워드 ∪ 시맨틱, 중복제거 top-K, 재랭크 없음)
     → RagRecommender(LLM 1콜: 후보 중 '선택: n,m' + 근거, 없으면 되묻기)
     → ProductEnricher(그라운딩·가격 결정적 부착) → SSE
```

- **질의 이해**를 둔다: 카탈로그 상품명이 영어라 한국어 원 질의가 검색을 놓친다(KO/EN 미스매치). LLM 1콜로 한/영 키워드·시맨틱 질의를 뽑아 검색 품질을 회복한다.
- **재랭크는 하지 않는다**(config5 최악의 원인). 리콜은 검색, 정밀도는 LLM 선택이 담당.
- **검색은 현재 질의로만** 구동한다(히스토리 무관) → 히스토리發 재검색·과고착 버그를 근본 해소. 히스토리는 프롬프트에 '이전 추천 참조용'으로만 넣는다.
- **호환(find_compatible) 제거**. 호환 관계는 이름·설명에 인코딩돼 키워드/시맨틱이 커버한다(실험 증거).
- `astream/run`·SSE 계약(token·status·recommendation·done)·멀티턴·가격·마크다운은 유지한다. 진행 상태는 `검색 중…` 1회.

**ADR-0007·0011·0013을 대체(supersede)** 한다.

## 이유

- **A/B 실증**: eval 하네스(250 코퍼스·31 질의·gpt-4o 심사)로 현재 에이전트(config4) vs RAG 비교 — RAG 절대 적합도 **1.968 vs 1.871**, 승률 **0.387 vs 0.226**(semantic 0.6 vs 0.2, structured 0.3 vs 0.2, keyword·compat 동률). RAG ≥ 에이전트. (근거: `.scratch/rag-recommender/RESULTS.md`)
- **예측가능성**: 검색이 결정적이라 같은 질의에 같은 결과, 히스토리 과고착 없음.
- **단순성**: LLM에게 도구 오케스트레이션을 시키지 않아 시스템 프롬프트가 2~3줄로 축소.
- **속도**: 2콜(질의이해+생성)로 에이전트 ~5콜 루프보다 첫 토큰이 빠름.

## 대안 (기각)

- **순수 RAG(질의 이해 없음)**: 라이브 트레이서에서 KO/EN 카탈로그 검색 실패('플라스크 추천해줘' 키워드 0·시맨틱 무관) — 질의 이해 1콜로 해결.
- **cross-encoder/LLM 재랭크(config5)**: 리트리벌 실험 최악(1.65) — 재랭크 대신 LLM 읽기.
- **에이전트 유지**: 비결정성·과고착·긴 프롬프트·느린 첫 토큰.
- **checkpointer 서버 세션**: 무상태 클라이언트 히스토리로 충분(ADR-0013 유지).

## 결과

- `RecommendationAgent`(StateGraph)·`GraphTools` 도구 래퍼·`TOOL_STATUS_LABELS`·7섹션 도구 프롬프트 제거. `GraphStore`·`SemanticSearch`·`ProductEnricher`·`ContextTrimmer`·히스토리는 유지.
- eval 하네스는 A/B 후 main에서 제거(재현은 eval 브랜치, 결과는 RESULTS.md).
- `.env`: `RAG_TOP_K`(검색 후보 수), 기존 `AGENT_TOKEN_BUDGET`·`AGENT_HISTORY_TURNS` 유지.
- 브라우즈/모호 질의는 LLM 되묻기로 처리(별도 브라우즈 역량은 후속).
