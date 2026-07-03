# Kolab KG Chat

실험·연구 장비 쇼핑몰을 위한 **적합성(fitness-for-purpose) 추천 챗봇**. 쇼핑몰 DB를 지식그래프(Knowledge Graph)로 만들고, 그 위에서 GraphRAG로 "무엇을 어떤 실험·환경에 쓰려는데 뭘 사야 할까?" 류의 질문에 답한다.

일반 검색과 다른 점: 단순 키워드/카탈로그 매칭이 아니라, 정규화된 **기능적 속성(Functional Attribute)** 과 **호환 관계**로 적합성을 판단하고, **추천 근거(Rationale)** 와 **상품 URL·이미지·근거 속성(Grounding)** 을 함께 제시한다.

용어·설계 배경은 [CONTEXT.md](CONTEXT.md)와 [docs/adr/](docs/adr/)를 참고.

## 주요 기능

- **React 챗 UI** — nginx가 단일 엔드포인트(:80)에서 프론트와 API를 함께 서빙
- **근거 있는 추천** — LLM 에이전트가 그래프를 검색해 추천 근거를 실시간(SSE) 스트리밍하고, 시스템이 각 상품에 **kolab 상품 URL·이미지·근거 속성**을 결정적으로 부착 (환각 차단)

## 동작 방식

```
[React SPA] ──/──┐
                 ├─▶ [nginx :80] ──▶ [Django Ninja API] ──▶ [Recommendation Agent (langgraph)]
[SSE /chat] ─────┘                                              │  tools: search/find/compatible/attributes/semantic
                                                                ▼
                                    [Knowledge Graph: Postgres + Apache AGE + pgvector]
                                                                ▲
                              [Source Connector] ◀── 고객사 소스 DB (읽기 전용)
```

- **읽기 경로**: `/chat`(SSE) → Recommendation Agent가 그래프 도구로 후보를 찾고 근거를 모아 추천을 스트리밍한다. ([ADR-0011](docs/adr/0011-tool-calling-agent-single-read-path.md))
- **쓰기 경로**: Source Connector가 고객사 DB를 읽어 Product를 조립하고 지식그래프에 적재한다. 지식그래프는 소스 DB의 복제본이 아니라 우리 스키마의 개념 모델이다.
- 적합성 신호는 정규화된 속성·관계에 있고, 여기에 **상품 텍스트 임베딩의 의미 유사도(`semantic_search`)를 결합**해 서술형·유의어 질의를 보강한다([ADR-0012](docs/adr/0012-reintroduce-embeddings-semantic-search.md), 리트리벌 실험 근거).

---

## 고객사 DB에 적용하기 (배포)

### 1. 사전 준비

- **Docker / Docker Compose**
- **OpenAI API 키** (추천 에이전트·속성 추출에 사용)
- **소스 DB 접속 정보** — 상품 데이터가 있는 쇼핑몰 DB. **읽기 전용(SELECT) 계정을 권장**한다 (시스템은 소스 DB에 쓰지 않는다). 컨테이너에서 해당 DB 호스트에 네트워크로 접근 가능해야 한다.

> **소스 스키마 전제**: 기본 커넥터는 **Youngcart/Gnuboard(그누보드5 쇼핑)** 스키마를 가정한다 — `g5_shop_item`(`it_id`, `it_name`, `it_brand`, `it_img1~30`, `ca_id`…), `g5_shop_item_option`, `g5_shop_item_field_info`. 스키마가 다르면 아래 [커스텀 커넥터](#다른-스키마를-쓰는-경우-커스텀-커넥터)를 참고.

### 2. `.env` 작성

`.env.example`를 복사해 채운다:

```bash
cp .env.example .env
```

```dotenv
# 필수
OPEN_AI_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini            # (선택) 추천/추출 모델
#EMBEDDING_MODEL=text-embedding-3-small  # (선택) semantic_search 임베딩 모델

# 고객사 소스 DB (읽기 전용 계정 권장)
SOURCE_DB_HOST=your-db-host
SOURCE_DB_PORT=3306
SOURCE_DB_USER=readonly_user
SOURCE_DB_PASSWORD=change-me
SOURCE_DB_NAME=your_shop_db

# 지식그래프(내장 Postgres) 비밀번호 변경 시 (선택)
#POSTGRES_PASSWORD=change-me
```

### 3. 기동 (prod)

prod 구성은 개발용 요소(모의 DB·코드 마운트·디버깅 포트)를 배제하고, 소스 DB는 `.env`의 `SOURCE_DB_*`(=고객사 DB)를 가리킨다.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

기동되는 서비스: `db`(지식그래프 저장소, AGE 포함 함께 배포) · `api` · `nginx`(:80) · `worker`(증분 동기화 — 6단계 참고).

### 4. 지식그래프 적재 (인제스트)

소스 DB의 상품을 지식그래프로 적재하는 관리 명령이다(멱등 — 여러 번 실행해도 안전).

> 참고: prod의 `worker`(6단계)가 첫 폴링에서 빈 그래프를 **자동으로 구조 적재**한다. 따라서 이 단계는 **즉시 적재**하거나 `--llm`으로 근거를 더 풍부하게 넣고 싶을 때 직접 실행한다.

```bash
# 전체 적재 (구조화 스펙: 브랜드 + field_info) — LLM 비용 없음, 빠름
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm api python manage.py ingest_products

# 옵션: --limit N (일부만) · --batch-size N (커밋 주기, 기본 500·INGEST_BATCH_SIZE)
#      · --llm (설명 텍스트에서 Functional Attribute까지 추출, 비용 발생)
```

- 기본은 **구조화된 스펙(브랜드·field_info)** 을 근거 속성으로 적재한다 — 대부분의 상품이 정형 스펙으로 커버되고 LLM 비용이 없다.
- **대규모 확장**: 키셋 스트리밍 + 배치 세션(커넥션 재사용) + 배치당 커밋으로 수십만~수백만 Product를 저사양 박스에서 감당한다. 적재 시작 시 필수 AGE 인덱스를 자동 생성한다(`manage.py ensure_indexes`로 별도 실행도 가능).
- `--llm`을 주면 상품 설명에서 재질·온도범위 등 Functional Attribute까지 LLM으로 추출해 근거가 풍부해진다(토큰 비용 발생).
- **의미 검색(임베딩, ADR-0012)**: 적재 시 상품 텍스트를 자동 임베딩해 `semantic_search`를 활성화한다 — 상품명 키워드로 못 잡는 서술형·유의어·한/영 미스매치 질의를 메운다(`text-embedding-3-small`, content-hash 게이팅으로 안 바뀐 상품은 재임베딩 안 함). 이미 적재된 그래프는 `manage.py embed_products`로 백필한다.
- 적재가 끝나면 챗봇이 바로 추천에 이 근거를 인용한다.

### 5. 접속

브라우저로 배포 호스트에 접속:

```
http://<배포-호스트>/
```

예) `내열성 좋은 유리 플라스크 추천해줘` → 추천 근거가 스트리밍되고, 상품 카드에 근거 속성과 실제 상품 URL이 표시된다.

### 6. 증분 동기화 (폴링 워커)

소스 DB의 변경분을 지식그래프에 반영하는 폴링 워커다. **prod 구성에는 `worker` 서비스가 포함되어 자동 실행된다**(`sync_poll --interval 3600`). 평소엔 **`it_update_time` 증분**(바뀐 상품만 assemble → watermark 전진)으로 **저부하**로 돌고, 안 바뀐 상품은 content-hash 게이팅으로 재처리를 생략한다([ADR-0008](docs/adr/0008-product-coalesced-current-state-sync.md)). 저빈도로 **전체 재조정**을 돌려 하드 삭제·드리프트를 보정한다(기본 24사이클마다, `--reconcile-every`). **소스 스냅샷이 비면(장애/오설정) 전량 삭제를 막는 안전장치**가 있고, `it_update_time`이 없으면 재조정으로 폴백한다.

```bash
# 크론용: 증분 1회 / 재조정 1회(삭제 보정)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm api python manage.py sync_poll --once
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm api python manage.py sync_poll --once --reconcile
```

- 워커가 불필요하면 prod 구성에서 `worker` 서비스를 제거하면 된다.
- 실시간·초저부하가 필요하면 binlog 기반 CDC로 대체한다([ADR-0002](docs/adr/0002-cdc-for-delta-sync.md)).

### 튜닝 (환경변수)

적재·동기화 옵션은 `.env`로 제어한다(자동 실행되는 `worker`는 CLI를 못 주므로 `.env`가 핵심). CLI 인자가 있으면 CLI가 우선한다.

| 변수 | 기본 | 설명 |
|------|------|------|
| `INGEST_BATCH_SIZE` | 500 | 적재 배치 크기(커밋 주기). 작을수록 메모리·트랜잭션 작고, 클수록 빠름 |
| `INGEST_PAGE_SIZE` | 1000 | 소스 id 키셋 페이지 크기(한 번에 가져오는 id 수) |
| `INGEST_LLM` | 0 | 1이면 적재 시 설명 텍스트에서 Functional Attribute까지 LLM 추출(비용) |
| `SYNC_INTERVAL` | 3600 | 워커 폴링 주기(초) |
| `SYNC_RECONCILE_EVERY` | 24 | N 사이클마다 전체 재조정(삭제·드리프트 보정). 0=하지 않음 |
| `SYNC_LLM` | 0 | 1이면 변경분을 LLM으로 재추출(비용) |
| `EMBEDDING_MODEL` | text-embedding-3-small | `semantic_search`·적재 임베딩 모델(ADR-0012). content-hash로 안 바뀐 상품은 재임베딩 안 함 |

> 예) 저사양 박스에서 메모리를 더 아끼려면 `.env`에 `INGEST_BATCH_SIZE=200`, `INGEST_PAGE_SIZE=500`. 소스 부하를 낮추려면 `SYNC_INTERVAL=21600`(6시간).

### 다른 스키마를 쓰는 경우 (커스텀 커넥터)

Youngcart/Gnuboard가 아니라면 **Source Connector** 하나만 새로 구현하면 된다 — 소스 스키마 지식을 여기에 가두므로 나머지 시스템은 소스 모양에 의존하지 않는다.

- 위치: [backend/apps/connectors/](backend/apps/connectors/) (기준 구현: `youngcart_mysql.py`, 인터페이스: `base.py`)
- 해야 할 일: `iter_product_ids()`로 상품 키를 나열하고, `assemble(id)`로 여러 row·테이블을 하나의 `ProductDocument`(이름·브랜드·카테고리·설명·이미지·옵션)로 조립한다.
- 이미지 URL은 커넥터에서 절대 URL로 정규화한다.

---

## 개발 / 데모 (dev)

개발용 구성은 `docker-compose.override.yml`이 자동 병합된다 — 번들 mock 소스 DB, 코드 라이브 리로드, 디버깅 포트를 포함한다.

```bash
# 실제 에이전트(OpenAI 키 필요)
docker compose up -d --build

# OpenAI 없이 결정적 데모/E2E — 스크립트 에이전트 + 데모 시드
AGENT_FAKE=1 docker compose up -d --build
docker compose run --rm api python seed_demo.py
#  → http://localhost/
```

테스트 / 프론트 타입 생성:

```bash
docker compose run --rm api pytest -q          # 백엔드 테스트
cd frontend && npm run orval                    # OpenAPI → 타입드 클라이언트
cd frontend && npm run e2e                       # Playwright E2E (위 AGENT_FAKE 스택 + seed 필요)
```

## 구성 개요

| 경로 | 설명 |
|------|------|
| [backend/](backend/) | Django + Django Ninja API, Recommendation Agent, 그래프 스토어, 커넥터, 인제스트 |
| [frontend/](frontend/) | React(Vite+TS) 챗 UI, Orval 생성 타입 |
| [nginx/](nginx/) | 단일 엔드포인트 리버스 프록시 + 프론트 정적 서빙(멀티스테이지 빌드) |
| [db/](db/) | Postgres + Apache AGE 커스텀 이미지 |
| [docs/adr/](docs/adr/) · [CONTEXT.md](CONTEXT.md) | 설계 결정(ADR)과 도메인 용어집 |
| `docker-compose.yml` | 베이스(공통) · `*.override.yml`(dev) · `*.prod.yml`(납품) |
