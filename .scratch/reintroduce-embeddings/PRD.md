# PRD — 임베딩·semantic_search 운영 재도입 (ADR-0012 구현)

Status: ready-for-agent

## Problem Statement

리트리벌 ablation 실험(RESULTS.md)에서 임베딩 기반 `semantic_search`를 쓰는 config가 검색 품질 최고(절대 2.42/3, 서술형 질의 2.9/3)로 나왔고, 임베딩 없는 경로는 서술형·유의어·한/영 미스매치 질의에서 뒤처졌다. 그런데 운영 읽기 경로(Recommendation Agent, ADR-0011)는 ADR-0010으로 임베딩을 제거해 이 질의들을 잘 못 잡는다. ADR-0012가 임베딩 재도입을 결정했으나 **운영 코드에는 아직 반영되지 않았다**.

## Solution

운영 경로에 임베딩을 되살린다(ADR-0012):

- **읽기**: Recommendation Agent가 `semantic_search` 도구로 의미 유사 상품을 후보에 넣어, 키워드·속성으로 못 잡는 서술형 질의를 메운다.
- **쓰기**: 상품 적재/동기화 시 Product 텍스트(name + 속성값)를 임베딩해 pgvector에 저장한다. 안 바뀐 상품은 재임베딩하지 않는다(content-hash 게이팅).
- **백필**: 이미 적재된 그래프의 상품을 한 번에 임베딩하는 명령을 제공한다.
- 사용자(챗봇)는 "액체를 정확히 옮기는 도구" 같은 서술형 질의에도 적절한 상품을 추천받는다.

## User Stories

1. 챗봇 사용자로서, "액체를 정확히 옮기는 도구"처럼 상품명에 없는 서술형·유의어로 물어도 적절한 상품을 추천받고 싶다.
2. 챗봇 사용자로서, 한국어로 물었는데 상품명이 영어여도(또는 반대) 의미로 매칭돼 추천받고 싶다.
3. 개발자로서, 추천 에이전트가 키워드·속성 검색과 함께 의미 유사도 검색을 도구로 쓰기를 원한다.
4. 납품 운영자로서, 상품을 적재하면 자동으로 임베딩되어 semantic_search가 바로 동작하기를 원한다.
5. 납품 운영자로서, 안 바뀐 상품은 재적재/동기화 시 재임베딩되지 않아(content-hash 게이팅) 비용이 절약되기를 원한다.
6. 납품 운영자로서, 이미 적재된 그래프의 상품을 한 번에 임베딩하는 백필 명령을 원한다.
7. 납품 운영자로서, 임베딩 모델을 환경변수로 지정/교체할 수 있기를 원한다(모델 버전 태깅).
8. 납품 운영자로서, 모델을 바꾸면 해당 임베딩만 점진 재생성되기를 원한다(버전 불일치 감지).
9. 개발자로서, 임베딩 저장·조회가 별도 딥모듈로 격리되어 결정적으로 테스트되기를 원한다.
10. 개발자로서, semantic_search 도구 추가가 기존 그래프 도구(search/find/compatible/get_attributes)와 공존하기를 원한다.
11. 개발자로서, 이 재도입이 이미 검증된 실험 하네스의 lean 구현을 승격하는 형태이기를 원한다(중복 최소화).
12. 아키텍트로서, vision은 재도입하지 않고(실험서 값 없음) 임베딩만 되살리기를 원한다.
13. 개발자로서, 임베딩 비용(text-embedding-3-small)이 저렴하고 캐시로 반복 비용이 억제되기를 원한다.
14. 개발자로서, 이 변경이 운영 읽기 경로 단일화(ADR-0011)를 깨지 않고 도구만 추가하기를 원한다.

## Implementation Decisions

- **EmbeddingStore (딥모듈)**: 실험 하네스의 lean 임베딩(`EvalEmbeddings`)을 운영 모듈로 승격한다. pgvector 테이블(`kg_embedding`)에 (source_id, name, model, text_hash, embedding) 저장. `embed_product(source_id, name, text)`는 (source_id, model) 기준 같은 text_hash면 스킵(캐시), 모델 버전을 태깅. `search(query, k)`는 같은 모델의 최근접 top-k를 반환. 프로바이더는 `OpenAIEmbeddingProvider`(text-embedding-3-small) / `FakeEmbeddingProvider`(결정적 테스트).

- **SemanticSearch 도구**: `search(keyword, k)` → top-k 상품(id·이름). 운영 knowledge_graph의 임베딩 저장소를 가리킨다. Recommendation Agent는 이미 `semantic_tool` 주입을 지원하므로(실험 config4), 운영 컨텍스트 조립에서 이를 연결한다.

- **읽기 경로 배선**: 운영 에이전트 컨텍스트를 만들 때 `semantic_search` 도구를 그래프 도구와 함께 구성한다. 도구 스키마·프롬프트는 실험에서 검증된 것을 재사용.

- **쓰기 경로 배선**: 적재 러너(IngestRunner)가 상품 반영 시 임베딩까지 수행한다. 임베딩 텍스트 = name + 속성값. **content-hash 게이팅 재사용** — 안 바뀐 상품(delta)이면 추출·임베딩을 함께 생략. 임베딩 프로바이더는 주입(운영=OpenAI, 테스트=Fake).

- **백필 명령**: 이미 적재된 knowledge_graph 상품을 순회하며 임베딩하는 관리 명령(예: `embed_products`). 캐시 덕에 재실행 안전.

- **모듈 위치**: ADR-0010으로 지웠던 `apps/embeddings`를 lean 형태로 되살리고, 실험 하네스(apps/eval)도 이를 재사용하도록 정리(중복 제거)한다. 단, 실험의 테이블 격리(별도 table 파라미터)는 유지.

- **범위 제한**: Product 텍스트 임베딩만(Application/Condition 노드 임베딩은 범위 밖, ADR-0009 lean). vision 재도입 없음.

- **환경변수**: 임베딩 모델은 `EMBEDDING_MODEL`(기본 text-embedding-3-small). 키는 기존 `OPEN_AI_KEY`.

## Testing Decisions

- 좋은 테스트는 **결정적 외부 동작**만 검증한다(임베딩 품질 자체가 아니라 배관: 저장·최근접·캐시·게이팅·도구 노출).
- 테스트 대상 모듈:
  - **EmbeddingStore**: FakeEmbeddingProvider로 최근접 검색 정확·임베딩 캐시(같은 텍스트 재호출 0, 카운팅)·모델 버전 태깅. (실험 test_eval_embeddings 승격.)
  - **IngestRunner 임베딩**: 적재 시 상품이 임베딩되고, content-hash 게이팅으로 안 바뀐 상품은 재임베딩 안 됨(카운팅 프로바이더).
  - **읽기 경로 배선**: 운영 컨텍스트가 semantic_search 도구를 포함(에이전트 도구 목록/동작).
  - **semantic_search 도구**: 가짜 임베더로 top-k 순위.
- 프리아트: `tests/test_eval_embeddings.py`(승격 대상), `tests/test_ingest_runner.py`(게이팅·카운팅), `tests/test_runtime.py`(컨텍스트 조립), 카운팅 커넥션/프로바이더 패턴.

## Out of Scope

- Application/Condition 노드 임베딩(구 ADR-0009 풀안) — 상품 텍스트만.
- vision 재도입(ADR-0005 저순위 유지).
- 하이브리드 융합+리랭킹(config5) — 실험서 실패, 별도 실험.
- 임베딩 인덱스(pgvector IVFFlat/HNSW) 튜닝 — 코퍼스 규모 커지면 별도.
- 실험 하네스(apps/eval) 자체의 재설계.

## Further Notes

- 관련 ADR: ADR-0012(이 PRD의 결정), ADR-0010(대체됨), ADR-0009(lean 부활), ADR-0003(pgvector 재활성), ADR-0011(읽기 경로 단일화 — 도구만 추가).
- 근거: `.scratch/retrieval-quality-eval/RESULTS.md`.
- 비용: text-embedding-3-small은 저렴 — 전 카탈로그도 수 달러 규모, content-hash 캐시로 반복 억제.
- 대규모 적재 시 임베딩이 인제스트 시간을 늘리므로, 배치·게이팅과 함께 모니터링.
