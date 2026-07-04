# 이슈 01: HybridRetriever (결정적 검색)

Status: done — HybridRetriever(키워드∪시맨틱, 재랭크X) + QueryAnalyzer(한/영 질의이해). 라이브: 플라스크→flask 정제로 검색 회복.
Type: AFK
Parent: .scratch/rag-recommender/PRD.md

## What to build

질의를 받아 후보를 결정적으로 뽑는 딥모듈. **키워드 검색(GraphStore.search_products) ∪ 시맨틱 검색(SemanticSearch)** 을 각각 돌려 `source_id`로 합집합·중복제거하고 top-K(기본 `RAG_TOP_K`≈20)를 남긴다. cross-encoder 재랭크는 하지 않는다(리콜 위주). 각 후보에 이름 + 속성(get_attributes)을 붙여 LLM이 적합성을 판단할 근거를 담는다. 히스토리는 쓰지 않는다(현재 질의만).

## Acceptance criteria

- [ ] `retrieve(query, k)`가 키워드·시맨틱 합집합·중복제거 후보를 top-K로 반환
- [ ] 각 후보에 source_id·이름·속성(그라운딩) 포함
- [ ] 한 소스가 비어도(키워드 0건 등) 다른 소스로 후보 산출
- [ ] top-K 절단 동작, `RAG_TOP_K`(.env) 반영
- [ ] fake 키워드/시맨틱 제공자로 결정적 단위 테스트(합집합·중복제거·절단)

## Blocked by

None - can start immediately
