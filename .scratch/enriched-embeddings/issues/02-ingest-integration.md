# 이슈 02: IngestRunner 통합 + RAG_ENRICH 플래그

Status: ready-for-agent
Type: AFK
Parent: .scratch/enriched-embeddings/PRD.md

## What to build

강화를 적재 경로에 배선한다. `IngestRunner.apply`가 속성 설정 뒤·임베딩 전에, **`RAG_ENRICH` 켜짐이면** DescriptionGenerator로 설명을 얻어(게이팅·캐시) **강화 텍스트(상품명 + 속성 값 + 설명)** 로 임베딩한다. 꺼짐(기본)이면 현행(name+값) 그대로 — 하위호환. content-hash 게이팅은 설명·임베딩 둘 다에 적용해 unchanged 상품은 생략. 설명 실패해도 현행 텍스트로 임베딩해 적재는 성공. `ingest_products`·`sync_poll`가 플래그에 따라 강화 임베더를 주입.

## Acceptance criteria

- [ ] `RAG_ENRICH=1`이면 강화 텍스트(name+값+설명)로 임베딩, `0`(기본)이면 현행
- [ ] content-hash로 unchanged 상품은 설명·임베딩 생략
- [ ] 설명 생성 실패 시 현행 텍스트로 임베딩(적재 성공)
- [ ] ingest_products·sync_poll가 플래그 따라 강화 임베더 배선
- [ ] 통합 테스트(fake describer): 강화 on→강화 텍스트, off→현행, 실패→폴백
- [ ] 라이브: 실 상품 적재 → 강화 임베딩 생성 확인

## Blocked by

- 이슈 01 (DescriptionGenerator + 캐시)
