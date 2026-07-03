# 04 — config 4: lean 임베딩 + semantic_search(캐시)

Status: done — EvalEmbeddings(pgvector, 임베딩 캐시) + SemanticSearch 도구, embed_corpus 명령(250 임베딩), config4 라이브 검증(시맨틱 질의→피펫). 테스트 test_eval_embeddings(2).

## Parent
`.scratch/retrieval-quality-eval/PRD.md`

## What to build

config 4(= config 3 + 임베딩)을 얹는다. lean 임베딩 모듈(pgvector, ADR-0009 방식 복원)로 코퍼스 Product당 name+설명+속성값을 text-embedding-3-small로 임베딩하고, 에이전트에 `semantic_search(query, k)` 도구를 추가한다(top-k 유사 상품 id). **임베딩은 (entity, model, text-hash) 키로 캐시** — 재실행 시 재계산하지 않는다. config 4 = config 3 도구 + semantic_search.

## Acceptance criteria

- [ ] 코퍼스 상품이 임베딩되고, 재실행 시 캐시 히트(재임베딩 없음, 카운팅 검증)
- [ ] `semantic_search(query,k)`가 유사도 top-k 상품 id를 반환한다(가짜 임베더로 순위 검증)
- [ ] config 4가 semantic_search + 그래프 도구를 함께 써 추천을 내고 EvalRunner에 캐시된다
- [ ] 실험 격리: 운영 읽기 경로(ADR-0011)는 임베딩을 쓰지 않는 상태 유지

## Blocked by
- 03 (config 3)
