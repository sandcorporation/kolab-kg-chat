# 07 — 수집 트레이서: ProductDocument → 그래프 → 질의

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

첫 진짜 end-to-end 트레이서. SourceConnector(#04)의 `ProductDocument`를 GraphStore(#06)로 흘려 Product/Variant(속성 추출은 아직 없음)를 그래프에 넣고, "상품 목록" 질의로 4종이 조회됨을 확인한다. 소스(MySQL)→그래프(Postgres) 전 구간이 한 번 관통된다.

## Acceptance criteria

- [ ] `iter_product_ids()` 순회 → 각 `assemble` → `upsert_product` 파이프가 동작
- [ ] Mock Source DB 4종이 그래프에 Product 노드로 존재
- [ ] 메스플라스크 19 Variant가 HAS_VARIANT로 연결됨
- [ ] "전체 Product 목록" 질의가 4종을 반환
- [ ] 통합 테스트: MySQL→Postgres 전 구간 1회 관통 검증

## Blocked by

- `04-source-connector.md`
- `06-graphstore-upsert.md`
