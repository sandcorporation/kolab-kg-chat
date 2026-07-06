# Kolab KG Chat — 배포 / 동작 확인 가이드

실험·연구 장비 쇼핑몰용 **적합성 추천 챗봇**입니다. 아래 순서대로 진행하시면 고객사 DB로 서비스를 띄우고 → 소량 데이터로 실제 동작을 확인하고 → 나머지를 전부 적재하고 → 변경분을 추적하는 워커까지 올리실 수 있습니다.

## 사전 준비

- **Docker / Docker Compose**
- **OpenAI API 키**
- **소스 DB 접속 정보** — 상품이 든 쇼핑몰 DB입니다. **읽기 전용(SELECT) 계정을 권장**합니다(시스템은 소스 DB에 쓰지 않습니다). 컨테이너에서 이 DB에 네트워크로 접근 가능해야 합니다.
  - 기본 커넥터는 **Youngcart/Gnuboard(그누보드5)** 스키마(`g5_shop_item`, `g5_shop_item_option`, `g5_shop_item_field_info`)를 가정합니다.

`.env.example`를 복사해 채워주세요:

```bash
cp .env.example .env
```

```dotenv
OPEN_AI_KEY=sk-...

# kolabshop_item DB (읽기 전용 계정 권장)
SOURCE_DB_HOST=your-db-host
SOURCE_DB_PORT=3306
SOURCE_DB_USER=readonly_user
SOURCE_DB_PASSWORD=change-me
SOURCE_DB_NAME=your_shop_db
```

> 배치 크기·폴링 주기·모델 등 나머지 옵션은 전부 `.env`로 제어합니다 — 전체 목록은 [.env.example](.env.example)를 참고해주세요.

아래 모든 명령은 **prod 구성**(dev용 모의 DB·디버깅 포트 배제)을 사용합니다. 반복을 줄이시려면 한 번만 지정해주세요:

```bash
export COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
```

---

## 1. 서비스 빌드 & 기동

검색 색인 저장소(`db`, Postgres + pgvector + pg_trgm) · API · 프론트(`nginx`, :80)를 빌드해 띄웁니다.
우리 DB엔 **임베딩·설명만** 담기고, 상품 사실(이름·가격·속성)은 채팅 때 소스에서 하이드레이션합니다(ADR-0016).
**워커는 4단계에서 올립니다** — 데이터를 넣기 전에 워커가 자동으로 전체 적재를 시작하지 않도록 여기서는 제외해주세요.

```bash
$COMPOSE up -d --build db api nginx
```

---

## 2. 동작 확인 — 수백 개만 먼저 적재

전체를 넣기 전에 소량(예: 300개)만 적재해 파이프라인이 실제로 도는지 확인해주세요. 멱등하므로 여러 번 실행하셔도 안전합니다.

```bash
$COMPOSE run --rm api python manage.py ingest_products --limit 300
#  → ingested into knowledge_graph: {'created': 300}
```

적재는 상품마다 **LLM 설명으로 강화한 임베딩**(검색용, ADR-0015)과 설명만 우리 DB에 저장합니다 — 상품 데이터는 복제하지 않습니다(C: 소스 하이드레이션, ADR-0016). 강화 임베딩은 한국어 질의가 영어 상품명을 찾도록 인덱스가 지능을 갖게 해, 채팅 때 질의 번역 LLM이 필요 없습니다(채팅당 LLM 1콜). content-hash로 안 바뀐 상품은 재생성을 건너뜁니다. 대규모 카탈로그의 최초 강화는 `embed_products`(동시성) 또는 Batch API로 합니다.

> 채팅 때 추천 카드의 이름·가격·속성·이미지는 **소스 DB에서 그 자리에서** 하이드레이션합니다(선택된 상품만 `it_id` 인덱스로 배치 조회). 따라서 **API가 적재와 동일한 `SOURCE_DB_*`를 보게** 해주세요 — 서로 다르면 카드가 비어 나옵니다.

브라우저로 접속해 질문해보세요:

```
http://<배포-호스트>/
```

예) `내열성 좋은 유리 플라스크 추천해줘` → 추천 근거가 실시간(SSE)으로 스트리밍되고, 상품 카드에 근거 속성·가격·실제 상품 URL이 붙습니다. **후속 질의**("방금 첫 번째 상품은 어디에 써?")도 이어집니다 — 무상태 멀티턴이라 프론트가 최근 대화를 함께 보냅니다(ADR-0013). 긴 대화는 토큰 예산으로 자동 트림됩니다(`AGENT_TOKEN_BUDGET`·`AGENT_HISTORY_TURNS`, [.env.example](.env.example) 참고).

---

## 3. 나머지 전체 적재

동작을 확인하셨으면 `--limit` 없이 전체를 적재해주세요. 2단계에서 넣은 상품은 content-hash로 걸러 재적재·재임베딩을 생략하므로, 이어서 나머지만 채웁니다.

```bash
$COMPOSE run --rm api python manage.py ingest_products
```

- 키셋 스트리밍 + 배치 커밋으로 수십만~수백만 상품도 저사양 박스에서 감당합니다.
- 시간이 오래 걸리면 `--batch-size N`으로 커밋 주기를 조절해주세요.

---

## 4. 변경분 추적 워커 띄우기

소스 DB의 생성·수정·삭제를 주기적으로 지식그래프에 반영하는 폴링 워커입니다. **전체 적재가 끝난 뒤** 올려주세요.

```bash
$COMPOSE up -d worker
```

- 평소엔 `it_update_time` **증분**(바뀐 상품만 반영)으로 저부하로 돌고, 안 바뀐 상품은 content-hash로 재처리를 생략합니다. 주기적으로 **전체 재조정**을 돌려 하드 삭제·드리프트를 보정합니다(소스 스냅샷이 비면 전량 삭제를 막는 안전장치 포함).
- 주기·재조정 간격은 `.env`로 제어합니다: `SYNC_INTERVAL`(초, 기본 3600) · `SYNC_RECONCILE_EVERY`(사이클, 기본 24).
- 크론에서 1회성으로 돌리시려면:
  ```bash
  $COMPOSE run --rm api python manage.py sync_poll --once              # 증분 1회
  $COMPOSE run --rm api python manage.py sync_poll --once --reconcile  # 재조정(삭제 보정)
  ```

전체 스택(워커 포함) 상태는 아래로 확인해주세요:

```bash
$COMPOSE ps
```
