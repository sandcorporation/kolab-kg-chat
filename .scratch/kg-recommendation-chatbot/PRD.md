# PRD — Kolab KG Chat: 실험장비 적합성 추천 챗봇

Status: ready-for-agent

## Problem Statement

실험·연구를 기획하는 사람은 "이런 실험을, 이런 환경에서, 이런 장비/시약을 쓰며 진행하려는데 무엇을 사야 하는가"를 판단해야 한다. 그러나 kolabshop 같은 실험장비 쇼핑몰은 브랜드·카테고리 중심으로 구성돼 있어, **용도·환경·호환**이라는 실제 의사결정 축으로는 상품을 찾기 어렵다. 결정적 스펙(재질·내열/내한·멸균등급·용량·측정범위·CAS 등)은 텍스트와 **이미지(스펙표)** 에 흩어져 있고, 사용자는 각 상품이 자기 실험에 맞는지, 이미 쓰는 장비와 호환되는지를 일일이 대조해야 한다.

## Solution

kolabshop의 데이터베이스를 **Knowledge Graph**로 변환하고, 그 위에서 **GraphRAG**로 **적합성(fitness-for-purpose) 추천**에 답하는 챗봇을 만든다. 사용자가 자연어로 실험 의도를 말하면, 시스템은 그 의도를 요구조건(Application·Condition)으로 풀고, Knowledge Graph의 **Functional Attribute**와 매칭해 상품을 추천하되 **"왜 이 상품인가"의 근거를 인용**한다. 답변은 실시간 토큰 스트리밍으로, 상품 카드·근거는 구조화 이벤트로 전달된다.

소스 DB는 미지의·변화하는 영역으로 보고, **SourceConnector** 라는 딥모듈 하나 뒤에 은닉한다. 실제 kolabshop DB가 도착하면 이 모듈만 교체하면 전체 파이프라인이 그대로 동작한다.

## User Stories

1. 실험 기획자로서, 나는 "초저온(-150℃ 이하) 세포 보관용 바이알 추천해줘"라고 물어, 내 보관 조건을 충족하는 상품을 받고 싶다.
2. 실험 기획자로서, 나는 "PCR에 쓸 0.2mL 튜브"처럼 응용(Application)으로 물어, 그 응용에 적합한 상품을 받고 싶다.
3. 실험 기획자로서, 나는 추천된 각 상품이 **어떤 Functional Attribute로 내 요구조건을 충족하는지** 근거를 보고 싶다(예: "재질=PTFE, 내열 -200~260℃라서").
4. 실험 기획자로서, 나는 추천 근거가 **소스 확정값인지 LLM 추측/이미지에서 읽은 값인지(provenance)** 구분해 보고 싶다.
5. 실험 기획자로서, 나는 "지금 ATAGO 점도계를 쓰는데 호환되는 표준액"처럼 **이미 쓰는 상품과의 호환(Compatibility)** 으로 추천받고 싶다.
6. 실험 기획자로서, 나는 같은 메스플라스크라도 **용량(50mL vs 500mL)** 에 따라 맞는 변형을 추천받고 싶다(기능 변형).
7. 실험 기획자로서, 나는 색상처럼 적합성과 무관한 외형 변형 때문에 추천이 중복으로 늘어나지 않기를 바란다.
8. 실험 기획자로서, 나는 모호하게 물었을 때 시스템이 **딱 한 번 명확화 질문**을 하거나 합리적 가정을 명시하고 진행해, 대화가 끊기지 않기를 바란다.
9. 실험 기획자로서, 나는 답변이 **실시간 토큰 스트림**으로 흘러, 기다림 없이 읽기 시작하고 싶다.
10. 실험 기획자로서, 나는 시약을 찾을 때 순도·CAS·포장 단위 같은 시약 고유 속성으로 매칭받고 싶다.
11. 실험 기획자로서, 나는 스펙이 이미지(스펙표)에만 있는 장비도 그 이미지에서 읽힌 속성으로 추천받고 싶다.
12. 실험 기획자로서, 나는 첫 검색이 0건이면 시스템이 제약을 한 번 완화해 대안을 제시하기를 바란다.
13. 운영자로서, 나는 초기 1회 전체 적재로 쇼핑몰 전 상품이 그래프에 들어오기를 바란다.
14. 운영자로서, 나는 상품이 생성·수정·삭제될 때마다 해당 상품이 자동으로 그래프에 반영되기를 바란다.
15. 운영자로서, 나는 한 상품에 변경이 몰려도(옵션 다건 동시 수정) 재추출이 **한 번만** 일어나 비용이 폭증하지 않기를 바란다.
16. 운영자로서, 나는 가격만 바뀐 경우 비싼 비전 LLM 재호출이 생략되기를(content-hash 게이팅) 바란다.
17. 운영자로서, 나는 delta 반영이 즉시가 아니어도(느슨한 지연) 무방하다.
18. 운영자로서, 나는 동시에 약 100개의 챗을 끊김 없이 처리할 수 있기를 바란다.
19. 운영자로서, 나는 LLM이 자율로 속성을 분류·추출하되, 저신뢰(특히 이미지 유래) 속성을 사후에 감사·교정할 수 있기를 바란다.
20. 개발자로서, 나는 실제 kolabshop DB 없이도 **mock MySQL(영카트 스키마)** 로 전체 파이프라인을 테스트하고 싶다.
21. 개발자로서, 나는 실제 DB가 도착하면 **SourceConnector 구현만 교체**하고 다운스트림은 손대지 않고 싶다.
22. 개발자로서, 나는 SourceConnector가 `ProductDocument`라는 source-agnostic 계약만 내보내, 다운스트림이 MySQL/영카트를 전혀 모르게 하고 싶다.
23. 개발자로서, 나는 GraphStore의 upsert가 소스 PK 기준 멱등이라, 재실행해도 노드/엣지가 중복되지 않기를 바란다.
24. 개발자로서, 나는 임베딩 모델을 교체해도 모델 버전 태그로 점진 재임베딩할 수 있기를 바란다.
25. 프론트엔드 개발자로서, 나는 Orval로 생성된 타입/REST 클라이언트를 쓰고, SSE 스트림만 얇은 수제 리더로 소비하고 싶다.
26. 프론트엔드 개발자로서, 나는 `token`/`recommendation`/`clarification`/`done`/`error` 이벤트 타입으로 분기해 토큰은 이어 붙이고 상품 카드는 구조로 렌더하고 싶다.
27. 운영자로서, 나는 비전 LLM/OpenAI 호출이 레이트 리밋에 걸려도 백오프·큐잉으로 견디기를 바란다.
28. 개발자로서, 나는 챗 읽기 경로와 수집/추출 쓰기 경로가 분리돼, 무거운 추출이 챗 지연을 해치지 않기를 바란다.

## Implementation Decisions

전반 결정은 `CONTEXT.md`(용어집)와 `docs/adr/0001~0009`를 따른다. 핵심:

- **Knowledge Graph는 개념 모델**이며 물리 저장은 **Postgres + Apache AGE + pgvector** 단일 인스턴스(AGE=깊은 순회, pgvector=유사도, SQL=속성 필터). [ADR-0003]
- **SourceConnector (딥모듈)** — 좁은 인터페이스 `iter_product_ids()`, `assemble(source_id) → ProductDocument`, `subscribe_changes() → AsyncIterator[ProductChanged]`. 첫 구현은 `YoungcartMySQLConnector`(영카트 `g5_shop_item`/`g5_shop_item_option`/`g5_shop_category` 스키마). 소스 SQL·옵션→Variant 매핑·가격 delta→절대값·`it_img*`→이미지·카테고리 계층·HTML 제거·content_hash를 모두 은닉. [ADR-0002, scope: kolabshop 특화]
- **`ProductDocument` 계약(스왑 seam)** — source-agnostic. 필드: `source_id`(=it_id, 멱등 upsert 키), `name`, `brand`, `category_path`, `description_text`, `images[]`(url·position), `variants[]`(variant_key·label·price·raw), `content_hash`, `raw`, `fetched_at`. 커넥터는 cosmetic/functional을 **판정하지 않고** 변형을 원형(raw)으로만 내보낸다(의미 판정은 추출 단계).
- **Product / Variant 모델** — Product는 여러 소스 row로 조립된 단위. Variant는 `HAS_VARIANT`로 연결. Functional Attribute는 *변하는 레벨*에 부착(공통→Product, 옵션마다 다름→Variant). Recommendation 매칭 단위 = 속성을 든 노드. [CONTEXT: Product/Variant/Matching Unit]
- **AttributeExtractor** — `ProductDocument` → Product Type 분류 → 유형별 통제어휘 Functional Attribute 추출. 텍스트 + **비전 LLM 직독**(고전 OCR 아님), ImageTriage로 스펙 이미지만 선별. cosmetic/functional 변형 판별은 추출의 부산물(옵션에서 어휘상 속성이 추출되면 functional). 모든 속성에 **provenance(`structured`/`llm_text`/`llm_ocr`) + confidence** 부착. [ADR-0001·0004·0005]
- **통제 어휘는 유형별**, 평평하지 않음. 핵심 차원 출발점: 재질·온도범위(min/max)·멸균등급·용량·호환규격·내화학성; 어휘는 "후보 적재→사람 승격" 루프로 성장. [ADR-0001]
- **GraphStore (딥모듈)** — 노드/엣지/속성 멱등 upsert(소스 PK 기준), 질의(속성 필터 + AGE 순회 + pgvector 유사도). [ADR-0003·0008]
- **SyncOrchestrator** — CDC 구독 → **Product 단위 코얼레싱/디바운스**(느슨한 지연) → 워커: assemble(현재상태 재조립, 멱등) → content-hash 게이트 → extract → upsert. 초기 전체 적재도 동일 경로. taskiq 워커. [ADR-0008]
- **EmbeddingModule** — Application·Condition 노드 + Product 서술텍스트를 `text-embedding-3-small`로 임베딩, 모델 버전 태깅. [ADR-0009]
- **읽기 경로(혼합 langgraph 에이전트)** — `RequirementParser`(질의→요구조건) → [모호 시 1회 clarification] → `Retriever`(AGE+SQL+pgvector 합성→랭킹) → [0건 시 제약 완화 1회 재검색] → `RecommendationComposer`(근거 인용). [ADR-0001]
- **ChatAPI** — Django + Django Ninja, ASGI, 전 구간 async(`aget`/`afilter`, async DB 드라이버, async OpenAI/redis). 턴 단위 인라인 스트리밍 POST, langgraph `astream_events()` + custom `StreamWriter`. **Redis pub/sub 미사용**(단일 테넌트, HITL 없음). [ADR-0006·0007]
- **SSE 프로토콜** — `event: {type}\ndata: {json}\n\n`. 타입: `token`/`recommendation`/`clarification`/`done`/`error`. [ADR-0007]
- **API 구조화** — Orval이 OpenAPI에서 타입+비스트리밍 REST 생성, SSE 스트림 소비만 수제 리더. [ADR-0007]
- **100 동시 처방** — I/O 바운드라 async가 해법. OpenAI 동시성 세마포어+백오프+큐잉(진짜 천장), 이벤트루프 비차단, Postgres 풀링, uvicorn 2+ 레플리카, 쓰기 경로 워커 분리. [ADR-0007]

## Testing Decisions

좋은 테스트는 **외부 행동만 검증**한다(구현 디테일 아님). LLM·비전 호출은 결정적 가짜 더블로 대체한다(embed-chat `fake_llm` 선례).

- **SourceConnector** (최우선, 지금 즉시) — mock MySQL(영카트 스키마, 실상품 4종 시드) 대상 통합 테스트: `assemble()`이 옵션을 Variant로, 가격 delta를 절대값으로, 카테고리를 경로로 올바르게 조립하는지; `iter_product_ids()`가 전 상품을 내는지; 산출 `ProductDocument`가 소스 무관 형태인지. 행동(입력 row → ProductDocument)만 검증, SQL 문자열은 검증하지 않는다.
- **GraphStore** — Postgres+AGE 컨테이너 대상 멱등 upsert(같은 PK 두 번 → 노드 1개), 속성 필터·AGE 순회·pgvector 질의 결과. prior art: embed-chat `test_graph_store_pg.py`, `test_graph_community.py`.
- **AttributeExtractor** — 가짜 LLM/비전으로 고정 `ProductDocument` → 기대 Functional Attribute(provenance 포함). cosmetic(색상) vs functional(용량) 변형 판별. prior art: embed-chat `test_ocr.py`, `fake_llm`.
- (후속) Retriever·RequirementParser·SSE 스트리밍 — 가짜 LLM + 테스트 클라이언트로 이벤트 시퀀스 검증(embed-chat `test_chat_streaming.py` 선례).

## Out of Scope

- 멀티테넌트/여러 쇼핑몰 동시 처리 (kolabshop 특화).
- HITL(상담원 개입) 및 지속 SSE + Redis pub/sub (필요해지면 embed-chat 패턴으로 승격).
- 도메인 온톨로지(실험→요구조건)의 사전 큐레이션 — LLM이 질의 시점에 다리 놓기, 검증된 매핑만 추후 승격.
- 결제·주문·재고 트랜잭션 (추천만).
- 실제 kolabshop DB 연결 (월요일 도착 후 SourceConnector 구현 교체로 흡수).
- 고전 OCR(PaddleOCR) — 비전 LLM 사용.

## Further Notes

- 실제 DB는 ~2026-06-29(월) 도착 예정. ADR-0002(CDC)는 그때까지 `proposed`(접근 권한 미확정). binlog/WAL 불가 시 폴링+주기적 대조로 후퇴.
- it_id 패턴(`DLM-4` 등 비숫자)으로 보아 kolabshop은 **영카트(그누보드)** 기반일 가능성이 높음 → mock 스키마를 영카트에 맞춰 월요일 교체 비용 최소화.
- 시드 상품 4종: 메스플라스크(ISOLAB, 용량 19변형/텍스트 스펙), 점도계 VISCO B(ATAGO, 이미지 스펙→OCR), PIPET PRO(색상 3변형=cosmetic), 중수소수 D₂O(CIL, CAS·포장 5변형).
