# 01 — EmbeddingStore 운영 모듈 승격 + 백필 명령

Status: ready-for-agent

## Parent
`.scratch/reintroduce-embeddings/PRD.md`

## What to build

실험 하네스의 lean 임베딩을 운영 딥모듈로 승격한다(ADR-0010으로 지운 `apps/embeddings` lean 부활). pgvector에 Product 텍스트 임베딩을 (source_id, name, model, text_hash, embedding)로 저장하고, 같은 텍스트면 재임베딩 스킵(캐시), 모델 버전 태깅, 최근접 top-k 검색을 제공한다. 이미 적재된 knowledge_graph 상품을 임베딩하는 백필 관리 명령도 만든다. 실험(apps/eval)도 이 모듈을 재사용하도록 정리한다(테이블 격리 유지).

## Acceptance criteria

- [ ] EmbeddingStore가 상품 텍스트를 임베딩·저장하고 최근접 top-k를 반환한다(FakeEmbeddingProvider로 검증)
- [ ] 같은 텍스트 재임베딩은 스킵(캐시 히트 — 카운팅 프로바이더로 재호출 0)
- [ ] 모델 버전이 태깅되고, 검색은 같은 모델끼리만 비교한다
- [ ] 백필 명령이 knowledge_graph 상품을 임베딩한다(재실행 안전)
- [ ] 실험 하네스가 승격 모듈을 재사용해도 기존 eval 테스트가 통과

## Blocked by
None - can start immediately
