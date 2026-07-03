# PRD — 저사양 인스턴스에서의 대규모 적재·동기화 최적화

Status: ready-for-agent

## Problem Statement

납품 환경이 cafe24 등 **가장 저렴한 단일 인스턴스(≈2GB RAM / 1 vCPU 올인원)** 인데, 고객사 카탈로그가 수십만~수백만 Product에 이를 수 있다. 현재 적재·동기화 경로는 이 규모에서 사실상 동작 불가다:

- GraphStore가 `MERGE/MATCH (p:Product {source_id})`를 쓰지만 **AGE에 속성 인덱스가 없어** 매 조회가 Product 전체 시퀀셜 스캔이다. 초기 적재가 **O(N²)** → 수백만 건이면 시간이 무한대에 수렴.
- GraphStore·Source Connector가 **메서드/상품 호출마다 새 커넥션**을 열고(Postgres는 매번 `LOAD 'age'`) 커넥션 처리량이 병목.
- `iter_product_ids`가 전체 id를 한 번에 버퍼링(비스트리밍)해 메모리 스파이크.
- Product 노드에 **읽기 경로가 쓰지 않는 상품 설명 HTML**(`it_explan`)을 통째로 저장해 디스크·성능을 낭비.
- 워커(Delta Sync)가 매 폴링마다 **전 상품을 재조립하는 재조정**이라 저사양 박스에 상시 과부하.
- Postgres·앱 프로세스가 2GB 예산 없이 기본값으로 떠 OOM-kill 위험.

## Solution

한 저가 박스에서 대규모 카탈로그를 감당하도록 적재·동기화를 최적화한다. 사용자(납품 운영자) 관점에서:

- **초기 적재**가 카탈로그가 커도 메모리 폭증 없이, 현실적 시간 안에 끝난다(배치·커넥션 재사용·인덱스).
- **증분 동기화**가 저부하로 상시 돈다 — 바뀐 상품만 반영하고, 삭제·드리프트는 저빈도 재조정으로 보정한다.
- 그래프가 불필요한 데이터로 비대해지지 않는다.
- 2GB 박스에서 OOM 없이 안정적으로 뜬다.

## User Stories

1. 납품 운영자로서, 수백만 Product 카탈로그를 초기 적재해도 워커가 메모리로 터지지 않기를 원한다 — 저가 박스가 죽지 않도록.
2. 납품 운영자로서, 초기 적재가 O(N²)가 아니라 규모에 선형에 가깝게 끝나기를 원한다 — 며칠이 아니라 현실적 시간에 끝나도록.
3. 납품 운영자로서, 적재가 배치 단위로 커밋되기를 원한다 — 중간 실패 시 처음부터 다시 하지 않도록.
4. 납품 운영자로서, 배치 크기를 환경변수로 조절하기를 원한다 — 박스 사양에 맞춰 메모리/속도를 튜닝하도록.
5. 납품 운영자로서, 적재가 소스·그래프 커넥션을 재사용하기를 원한다 — 상품마다 커넥션을 새로 열어 느려지지 않도록.
6. 납품 운영자로서, 상품 id를 전량 메모리에 올리지 않고 스트리밍 처리하기를 원한다 — id 리스트만으로 메모리 스파이크가 나지 않도록.
7. 납품 운영자로서, 그래프에 읽기 경로가 쓰지 않는 상품 설명 HTML이 저장되지 않기를 원한다 — 디스크·조회 성능을 아끼도록.
8. 챗봇 사용자로서, 카탈로그가 수백만이어도 추천 조회(상품 조회·속성 필터·호환 탐색)가 인덱스로 빠르기를 원한다.
9. 납품 운영자로서, 그래프 인덱스가 셋업 시 자동·멱등으로 생성되기를 원한다 — 수동 DBA 작업 없이.
10. 납품 운영자로서, 인덱스를 재생성/점검하는 관리 명령이 있기를 원한다.
11. 납품 운영자로서, 워커가 매 주기 전 상품을 재조립하지 않고 `it_update_time` 기준 바뀐 상품만 처리하기를 원한다 — 상시 저부하로.
12. 납품 운영자로서, 워커가 마지막으로 처리한 지점(watermark)을 영속해 재시작 후에도 이어서 감지하기를 원한다.
13. 납품 운영자로서, 하드 삭제·드리프트가 저빈도 전체 재조정(예: 야간 1회)으로 결국 보정되기를 원한다.
14. 납품 운영자로서, 소스에 `it_update_time`이 없으면 워커가 재조정으로 안전하게 폴백하기를 원한다.
15. 납품 운영자로서, 이미 반영된(안 바뀐) 상품은 content_hash 게이팅으로 재추출을 생략하기를 원한다.
16. 납품 운영자로서, Postgres가 2GB 박스에 맞게 튜닝되어 뜨기를 원한다 — 기본값으로 메모리를 과점하지 않도록.
17. 납품 운영자로서, compose 서비스별 메모리 상한이 있어 한 프로세스가 박스를 OOM-kill로 몰지 않기를 원한다.
18. 납품 운영자로서, 대량 적재 세션이 `synchronous_commit=off` 등으로 빨라지기를 원한다.
19. 개발자로서, 이 최적화들이 기존 추천/근거 동작(Recommendation·Rationale·Grounding)을 바꾸지 않기를 원한다 — 순수 성능·확장성 개선이도록.
20. 개발자로서, 적재/동기화 로직이 결정적 테스트로 커버되기를 원한다 — 배치·인덱스·증분·재조정이 회귀하지 않도록.

## Implementation Decisions

- **대상 환경**: 2GB RAM / 1 vCPU 단일 인스턴스 올인원(Postgres+AGE·api·nginx·worker). 동시성 없이 순차 처리 — 1 vCPU에서 병렬 이득이 적고 메모리·커넥션 압박이 크다.

- **AGE 인덱스 (딥모듈: GraphStore)**: 그래프 셋업 시 멱등으로 btree 인덱스를 생성한다 — `Product.source_id`(필수), `Variant.variant_key`, `Attribute.name`, `Attribute.value`. AGE 정점 테이블의 properties 접근 표현식에 대한 인덱스로, `MERGE/MATCH {source_id}`와 속성 필터를 시퀀셜 스캔에서 인덱스 조회로 바꿔 초기 적재를 O(N²)→O(N log N)로 만든다. `search_products`의 이름 부분일치(CONTAINS)는 이번 범위 밖(추후 pg_trgm).

- **커넥션 재사용 (딥모듈: GraphStore 배치 세션)**: 배치 동안 하나의 Postgres 커넥션(+`LOAD 'age'`·search_path 1회)을 재사용하고 배치 단위로 커밋한다. 기존의 "메서드마다 새 커넥션+autocommit" 대신, 주입된 커넥션 위에서 실행하는 세션 모드를 추가한다. 인터페이스 표면(메서드 이름)은 유지하되 공용 커넥션/커밋 제어를 받는다. 대량 적재 세션은 `synchronous_commit=off`.

- **스트리밍·키셋 (Source Connector)**: `iter_product_ids`를 `it_id` 키셋 페이지네이션으로 바꿔 전량 버퍼링을 없앤다. 배치 크기만큼씩 가져온다. `assemble`은 배치 동안 소스 커넥션을 재사용한다.

- **노드 페이로드 축소 (GraphStore.upsert_product)**: `p.description` 저장을 제거한다(읽기 경로 미사용). `--llm` 추출은 그래프가 아니라 조립 시점의 ProductDocument.description_text를 쓰므로 영향 없다.

- **배치 러너 (IngestRunner)**: `full_load`를 키셋 스트리밍 + 배치 세션 + 배치당 커밋으로 재구성한다. 배치 크기 기본 500, `INGEST_BATCH_SIZE`(및 `--batch-size`)로 조절. 상품은 1건씩 처리·해제(순차)라 peak 메모리는 배치·1 doc·트랜잭션으로 바운드.

- **증분 Delta Sync (SyncWatermark + Connector.changed_since + 워커)**:
  - 커넥터에 `it_update_time > watermark`인 변경 Product를 산출하는 조회와, 관측된 최대 `it_update_time`을 반환하는 방법을 둔다.
  - **SyncWatermark(딥모듈)**: 작은 Postgres 테이블(`sync_state`, key→value)에 마지막 watermark를 영속한다.
  - 워커(`sync_poll`): 평소엔 증분(변경 Product만 assemble, content_hash 게이팅 유지) → watermark 전진. 저빈도(예: 야간)로 전체 재조정을 돌려 하드 삭제·드리프트를 보정한다(배치 스트리밍). `it_update_time`이 없으면 재조정으로 폴백.
  - 재조정 시 빈 소스 안전장치(기존)와 배치 처리를 유지한다.

- **튜닝·가드레일 (db 이미지 / compose)**: db 이미지에 2GB용 `postgresql.conf`(예: shared_buffers ~256MB, work_mem 작게, maintenance_work_mem 상향 — 인덱스 빌드용). compose 서비스별 `mem_limit`로 예산 배분(api/worker/db). prod 조합에 적용.

- **관리 명령**: `ingest_products`(배치·`--batch-size`), `sync_poll`(증분 + `--reconcile`/주기 재조정), `ensure_indexes`(인덱스 멱등 생성/점검). 기존 명령 표면 유지·확장.

- **테스트 픽스처**: mock `g5_shop_item`에 `it_update_time`(및 `it_time`) 컬럼과 값을 추가해 증분 경로를 결정적으로 테스트한다(실제 Gnuboard5 스키마에도 존재).

## Testing Decisions

- 좋은 테스트는 **공개 인터페이스로 외부 동작만** 검증한다 — 내부 cypher 문자열이 아니라 "적재 후 그래프 상태·조회 결과·멱등성". 예외적으로 이번 최적화의 **계약 자체가 성능 특성**인 지점(커넥션 재사용)은 주입한 카운팅 커넥션 팩토리로 "배치당 커넥션 1회(상품마다 아님)"를 검증한다.
- 테스트 대상 모듈:
  - **GraphStore**: `ensure_indexes` 멱등·인덱스 존재(pg 카탈로그 조회), `upsert_product`가 description을 저장하지 않음, 배치 세션이 커넥션을 재사용(카운트).
  - **Source Connector**: 키셋 `iter_product_ids`가 전 id를 순서대로 산출·limit 동작, `changed_since(watermark)`가 변경분만 산출(mock `it_update_time` 기준).
  - **SyncWatermark**: set/get 왕복, 재시작 시뮬레이션.
  - **IngestRunner**: 배치 `full_load`가 전량 적재·멱등, 배치 커밋, 커넥션 카운트 바운드.
  - **워커 경로**: 증분이 바뀐 상품만 감지, 재조정이 삭제 감지·빈 소스 가드, watermark 전진.
- 프로토콜/프리아트: `tests/test_ingest_runner.py`, `tests/test_delta.py`, `tests/test_source_connector.py`, `tests/test_graph_store*` 스타일(도커 내 실제 Postgres+AGE·mock source-db, `graph_name="kg_test"`, `asyncio_mode=auto`).

## Out of Scope

- `search_products` 이름 부분일치 가속(pg_trgm GIN) — 이번 범위 밖.
- 동시성/병렬 적재, 커넥션 풀 기반 워커 — 1 vCPU 전제라 제외.
- 실제 CDC(binlog/WAL) — 폴링 증분/재조정으로 갈음(ADR-0002는 향후).
- 다중 노드·수평 확장, 외부 관리형 Postgres.
- 추천/근거 로직 변경(순수 성능·확장 개선).
- Vision 파이프라인.

## Further Notes

- 관련 ADR: 그래프 저장(ADR-0003, pgvector 축은 ADR-0010로 제거됨), current-state·content-hash 동기화(ADR-0008), CDC 폴링 fallback(ADR-0002), 에이전트 단일 읽기 경로(ADR-0011).
- 인덱스·커넥션 재사용은 초기 적재뿐 아니라 워커 증분·챗 조회에도 함께 이득.
- 커넥션 재사용은 GraphStore의 커넥션 수명 모델을 바꾸는 가장 큰 변경이라 딥모듈 세션으로 격리해 테스트한다.
