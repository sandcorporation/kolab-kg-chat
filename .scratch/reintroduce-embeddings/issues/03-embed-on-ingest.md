# 03 — 적재/동기화 시 임베딩(content-hash 게이팅)

Status: done — IngestRunner embedder 주입 + apply에서 임베딩(게이팅 뒤, 실패 격리). ingest_products·sync_poll 명령 배선. 라이브 검증(kg_embedding 4). 테스트 test_ingest_embedding(2).

## Parent
`.scratch/reintroduce-embeddings/PRD.md`

## What to build

적재 러너(IngestRunner)가 상품 반영 시 임베딩까지 수행한다. 임베딩 텍스트 = name + 속성값. **content-hash 게이팅 재사용** — delta에서 안 바뀐 상품은 추출·임베딩을 함께 생략한다. 임베딩 프로바이더는 주입(운영=OpenAI, 테스트=Fake). 이로써 새로 적재/변경된 상품이 자동으로 semantic_search 대상이 된다.

## Acceptance criteria

- [ ] `ingest_products`/`sync_poll`로 적재된 상품이 자동 임베딩된다
- [ ] content-hash로 안 바뀐 상품은 재임베딩되지 않는다(카운팅 프로바이더로 검증)
- [ ] 임베딩 실패가 상품 적재 자체를 막지 않는다(격리)
- [ ] 기존 적재 동작(속성 반영 등) 회귀 없음

## Blocked by
- 01 (EmbeddingStore)
