# Kolab KG Chat — 배포 / 동작 확인 가이드

실험·연구 장비 쇼핑몰용 **적합성 추천 챗봇**. 아래 순서대로 하면 고객사 DB로 서비스를 띄우고 → 소량 데이터로 실제 동작을 확인하고 → 나머지를 전부 적재하고 → 변경분을 추적하는 워커까지 올릴 수 있다.

## 사전 준비

- **Docker / Docker Compose**
- **OpenAI API 키**
- **소스 DB 접속 정보** — 상품이 든 쇼핑몰 DB. **읽기 전용(SELECT) 계정 권장**(시스템은 소스 DB에 쓰지 않는다). 컨테이너에서 이 DB에 네트워크로 접근 가능해야 한다.
  - 기본 커넥터는 **Youngcart/Gnuboard(그누보드5)** 스키마(`g5_shop_item`, `g5_shop_item_option`, `g5_shop_item_field_info`)를 가정한다.

`.env.example`를 복사해 채운다:

```bash
cp .env.example .env
```

```dotenv
OPEN_AI_KEY=sk-...

# 고객사 소스 DB (읽기 전용 계정 권장)
SOURCE_DB_HOST=your-db-host
SOURCE_DB_PORT=3306
SOURCE_DB_USER=readonly_user
SOURCE_DB_PASSWORD=change-me
SOURCE_DB_NAME=your_shop_db
```

> 배치 크기·폴링 주기·모델 등 나머지 옵션은 전부 `.env`로 제어한다 — 전체 목록은 [.env.example](.env.example) 참고.

아래 모든 명령은 **prod 구성**(dev용 모의 DB·디버깅 포트 배제)을 쓴다. 반복을 줄이려 한 번만 지정:

```bash
export COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
```

---

## 1. 서비스 빌드 & 기동

지식그래프 저장소(`db`, Apache AGE 포함) · API · 프론트(`nginx`, :80)를 빌드해 띄운다.
**워커는 4단계에서 올린다** — 데이터를 넣기 전에 워커가 자동으로 전체 적재를 시작하지 않도록 여기서는 제외한다.

```bash
$COMPOSE up -d --build db api nginx
```

---

## 2. 동작 확인 — 수백 개만 먼저 적재

전체를 넣기 전에 소량(예: 300개)만 적재해 파이프라인이 실제로 도는지 확인한다. 멱등하므로 여러 번 실행해도 안전하다.

```bash
$COMPOSE run --rm api python manage.py ingest_products --limit 300
#  → ingested into knowledge_graph: {'created': 300}
```

적재 내용: 상품 구조 스펙(브랜드·field_info)을 근거 속성으로, 그리고 상품 텍스트 임베딩(`semantic_search`용)까지. LLM 추출 없이 빠르고 저비용이다.

브라우저로 접속해 질문해 본다:

```
http://<배포-호스트>/
```

예) `내열성 좋은 유리 플라스크 추천해줘` → 추천 근거가 실시간(SSE) 스트리밍되고, 상품 카드에 근거 속성과 실제 상품 URL이 붙는다.

---

## 3. 나머지 전체 적재

동작을 확인했으면 `--limit` 없이 전체를 적재한다. 2단계에서 넣은 상품은 content-hash로 걸러 재적재·재임베딩을 생략하므로, 이어서 나머지만 채운다.

```bash
$COMPOSE run --rm api python manage.py ingest_products
```

- 키셋 스트리밍 + 배치 커밋으로 수십만~수백만 상품도 저사양 박스에서 감당한다.
- 시간이 오래 걸리면 백그라운드로 돌리고(`nohup … &`), `--batch-size N`으로 커밋 주기를 조절한다.

---

## 4. 변경분 추적 워커 띄우기

소스 DB의 생성·수정·삭제를 주기적으로 지식그래프에 반영하는 폴링 워커. **전체 적재가 끝난 뒤** 올린다.

```bash
$COMPOSE up -d worker
```

- 평소엔 `it_update_time` **증분**(바뀐 상품만 반영)으로 저부하로 돌고, 안 바뀐 상품은 content-hash로 재처리를 생략한다. 주기적으로 **전체 재조정**을 돌려 하드 삭제·드리프트를 보정한다(소스 스냅샷이 비면 전량 삭제를 막는 안전장치 포함).
- 주기·재조정 간격은 `.env`로 제어: `SYNC_INTERVAL`(초, 기본 3600) · `SYNC_RECONCILE_EVERY`(사이클, 기본 24).
- 크론에서 1회성으로 돌리고 싶으면:
  ```bash
  $COMPOSE run --rm api python manage.py sync_poll --once              # 증분 1회
  $COMPOSE run --rm api python manage.py sync_poll --once --reconcile  # 재조정(삭제 보정)
  ```

전체 스택(워커 포함) 상태 확인:

```bash
$COMPOSE ps
```
