# 04 — SourceConnector → ProductDocument (딥모듈)

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

소스 DB를 은닉하는 **딥모듈** `SourceConnector`. 좁은 인터페이스:
- `iter_product_ids() → AsyncIterator[str]` (초기 전체 적재용)
- `assemble(source_id) → ProductDocument | None` (현재 상태 재조립, 멱등 — ADR-0008)
- `subscribe_changes() → AsyncIterator[ProductChanged]` (CDC 자리, 지금은 stub/no-op)

첫 구현 `YoungcartMySQLConnector`는 영카트 SQL·옵션→Variant 매핑·**가격 delta→절대값**·`it_img*`→이미지·카테고리 계층 해석·HTML 제거·`content_hash` 계산을 전부 은닉한다.

출력 계약 `ProductDocument`(source-agnostic): `source_id`(=it_id), `name`, `brand`, `category_path[]`, `description_text`, `images[]`(url·position), `variants[]`(variant_key·label·price·raw), `content_hash`, `raw`, `fetched_at`. 커넥터는 cosmetic/functional을 **판정하지 않고** 변형을 원형으로만 내보낸다(의미 판정은 #08·#09).

이것이 월요일 실제 DB 교체의 단일 seam(#26)이다.

## Acceptance criteria

- [ ] `assemble("1548728629")` → 메스플라스크가 19개 Variant(라벨·절대가격)로 조립됨
- [ ] 가격이 `it_price + io_price`로 절대값 변환됨(점도계 ATAGO6865 = 6,182,000)
- [ ] `category_path`가 계층 ca_id에서 이름 경로로 해석됨
- [ ] `iter_product_ids()`가 시드 4종을 모두 산출
- [ ] 같은 입력에 `assemble`을 두 번 호출하면 동일한 `content_hash`(멱등)
- [ ] `ProductDocument`에 MySQL/영카트 용어가 새지 않음(소스 무관 형태)
- [ ] 통합 테스트: Mock Source DB(#03) 대상, 행동(row→ProductDocument)만 검증(SQL 문자열 검증 금지)

## Blocked by

- `03-mock-source-db.md`
