# Kolab KG Chat

실험·연구 장비 쇼핑몰을 위한 챗봇. 쇼핑몰 DB를 지식그래프로 만들고, 그 위에서 GraphRAG로 적합성(fitness-for-purpose) 추천 질의에 답한다 — "~~ 실험을 ~~ 환경에서 ~~를 쓰며 기획 중인데, 무엇을 사야 할까?". 그래프의 가치는 브랜드·카탈로그 계층이 아니라 **기능적 적합성**(응용·조건·호환)에 있다. 소스 DB는 미지의, 변화하는 영역으로 보고 소스별 커넥터를 통해 접근한다.

## Language

**Knowledge Graph**:
챗봇의 답변을 뒷받침하는 엔티티-관계 그래프 저장소. Product·Variant·Application·Condition과 그 관계를 담고 GraphRAG 방식으로 질의된다. 소스 DB의 복제본이 아니다. **개념 모델**이라 저장 엔진과 무관하다(현재는 Postgres+AGE에 우리 스키마로 저장). LangGraph의 실행 그래프(에이전트 제어 흐름)와는 전혀 다른 것이다.
_지양_: 벡터 저장소(vector store)·임베딩 색인(이 프로젝트는 벡터를 쓰지 않는다, ADR-0010), LangGraph graph(에이전트 상태 머신을 가리킴)

**GraphRAG**:
이 프로젝트의 검색 방식. Knowledge Graph에서 키워드(상품명)·Functional Attribute 필터·Compatibility 관계 순회로 후보를 검색하고, 그 근거(Grounding)로 LLM의 Rationale을 뒷받침한다. 벡터 의미유사도는 쓰지 않는다 — 적합성 신호는 정규화된 속성과 관계에 있다(ADR-0010).
_지양_: vector search/시맨틱 검색(이 프로젝트는 안 씀), embedding retrieval

**Application**:
고객이 기획 중인, 상품을 매칭할 대상이 되는 목적(예: PCR, 세포배양, 초저온 보관, 점도 측정). 단일 실험보다 넓은 개념으로 보관·측정·분석을 포함한다.
_지양_: experiment, 실험, use case, 용도, purpose

**Condition**:
어떤 Application을 위해 상품이 충족해야 하는 환경적·운영적 제약(예: 온도 영역, 멸균 등급, 내화학성, 클린룸 등급).
_지양_: environment, 환경, requirement, 요구사항

**Product**:
추천의 대상이 되는 개념적 상품(예: PIPET PRO). 소스 DB의 **여러 row·여러 테이블**(본체·옵션·이미지·스펙)에서 조립된 단위이지, 소스의 row 한 줄이 아니다. 그래프 노드의 기본 단위.
_지양_: row, 행, item, SKU(이건 Variant)

**Variant**:
한 Product의 구매 가능한 형태로, 옵션(색상·크기·용량 등)으로 구분됨. `Product -[HAS_VARIANT]-> Variant`로 연결. **외형 변형**(색상 등, 기능 적합성 무관)과 **기능 변형**(용량·측정범위 등, 서로 다른 요구를 충족)으로 나뉜다.
_지양_: option, 옵션, SKU

**Matching Unit**(매칭 규칙):
Functional Attribute는 *그것이 달라지는 레벨*에 붙인다 — 공통이면 Product, 옵션마다 다르면 Variant. Recommendation의 매칭 단위는 해당 속성을 들고 있는 노드다. 따라서 외형 변형은 Product로 합쳐지고, 기능 변형은 각자 매칭 대상이 된다.

**Product Type**:
어떤 Functional Attribute가 결정적인지를 정하는 상품 분류 축(예: 소모품/유리, 전동 피펫, 원심분리기, 시약). 통제 어휘는 평평하지 않고 Product Type별로 다른 속성 집합을 가진다. 쇼핑몰의 마케팅용 카테고리 계층과 같을 수도, 다를 수도 있다.
_지양_: category, 카테고리(마케팅 계층을 가리킬 때만 사용)

**Functional Attribute**:
적합성을 결정하며 추천이 인용할 수 있는, 정규화된 이름 붙은 상품 속성. **결정적인 속성 집합은 Product Type마다 다르다** — 유리 소모품은 재질·온도범위·내화학성·멸균·용량, 전동 기기는 측정범위·정밀도·전원·인터페이스·호환부속 등. 이것이 추출되어 나온 원시 스펙 텍스트와는 구별된다.
_지양_: spec, 스펙, feature, 기능, property, 속성값

**Compatibility**:
상품 대 상품의 관계 — 한 상품이 다른 상품의 부속품이거나, 소모품이거나, 함께 작동함(예: 로터가 원심분리기에 맞음, 캡이 튜브에 맞음).
_지양_: accessory, 부속, fits

**Recommendation**:
적합성 질의에 대한 시스템의 답. 추천 Product들의 집합이며, 각 상품은 질의의 Application·Condition을 충족하는 Functional Attribute와 짝지어진다. 답은 두 부분으로 이뤄진다 — 말로 된 Rationale과 각 상품의 Grounding(정본 URL·이미지·근거 속성). Rationale이나 Grounding이 빠진 Recommendation은 불완전하다.
_지양_: result, 결과, suggestion, 제안, match

**Rationale**(추천 근거):
Recommendation에 딸린, Recommendation Agent가 생성하는 자연어 근거. 도구로 확인한 Functional Attribute에 기반해 "왜 이 상품이 적합한가"를 설명한다. 카탈로그에 없는 상품·속성·링크를 지어내지 않으며(환각 차단, ADR-0001), 상품 URL·이미지는 시스템이 결정적으로 붙인다.
_지양_: explanation(너무 일반적), answer/답변(Recommendation 전체를 가리킴), summary/요약

**Grounding**:
한 추천 Product의 검증 가능한 근거 묶음 — 그 Product의 Functional Attribute(이름·값·Provenance)와 정본 상품 URL·이미지. Rationale이 말로 설명하는 바를 데이터로 뒷받침한다. LLM이 아니라 시스템이 그래프에서 결정적으로 조립한다.
_지양_: evidence(무엇의 근거인지 불명확), metadata, tags

**Provenance**:
한 Functional Attribute 값의 출처 — `structured`(소스의 정형 스펙, 예: field_info), `llm_text`(상품 설명 텍스트에서 LLM 추출), `llm_ocr`(상품 이미지에서 Vision LLM 추출). confidence와 함께 붙어 근거의 신뢰 수준을 밝힌다(ADR-0004).
_지양_: source(Source DB/Connector와 혼동), origin

**Recommendation Agent**:
읽기 경로를 이끄는 도구 호출(tool-calling) 에이전트. 그래프 도구(search_products·find_products·find_compatible·get_attributes)로 근거를 모으고 `recommend(ids)`로 최종 선택을 선언한 뒤 Rationale을 스트리밍한다. 이것은 LangGraph 실행 그래프(제어 흐름)이지 Knowledge Graph(개념 저장소)가 아니다.
_지양_: chatbot/봇(제품 전체를 가리킴), pipeline(구 비스트리밍 경로), chain

**Source Connector**:
미지의·변화하는 Source DB를 우리 도메인으로 옮기는 소스별 어댑터. 여러 row·테이블을 조립해 Product(및 Variant·이미지·원시 스펙)를 만든다. 소스 스키마 지식을 여기에 가둬 나머지 시스템이 소스 모양에 의존하지 않게 한다. 납품 시 고객사 DB 접속정보로 가리킨다.
_지양_: importer, ETL, scraper, sync(Delta Sync는 별개)

**Delta Sync**:
소스의 변경분만 반영해 Knowledge Graph를 최신으로 유지하는 동기화. Product 단위로 합쳐진 현재 상태를 content_hash로 게이팅해 바뀐 Product만 재처리한다(ADR-0008). 변경 데이터 캡처(CDC)를 지향한다(ADR-0002).
_지양_: reindex, full sync, migration, 재적재
