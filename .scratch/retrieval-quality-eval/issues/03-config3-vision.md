# 03 — config 3: vision 강화(sparse 상품, 캐시)

Status: done — vision 병합+per-product 캐시 인프라(테스트 2), config3 provenance 노출, enrich_corpus_vision 명령. 실행 발견: image_only 상품은 외부CDN(Sigma) 또는 상품사진이라 vision 기여 거의 없음(2개만 추출).

## Parent
`.scratch/retrieval-quality-eval/PRD.md`

## What to build

config 3(= config 2 + vision)을 얹는다. 코퍼스 중 **구조 스펙 부족 상품(이미지-only/희소)에만** ImageAttributeExtractor를 실행해 이미지에서 스펙을 추출하고(provenance=llm_ocr), 실험 그래프에 속성으로 붙인다. **기존 vision_cache(Postgres+JSON)를 재사용** — 이미 캐시된 상품은 재계산하지 않는다. config 3은 provenance={structured, llm_ocr}를 노출한다.

## Acceptance criteria

- [ ] sparse 상품에 vision 추출 속성(llm_ocr)이 그래프에 붙는다
- [ ] 이미 캐시된 vision 결과는 재실행 시 재계산하지 않는다(비용 0 — 캐시 히트 검증)
- [ ] config 3이 config 2가 못 보던 llm_ocr 속성을 근거로 쓸 수 있다(provenance 필터 차이)
- [ ] config 3이 코퍼스 위에서 추천을 내고 EvalRunner에 캐시된다

## Blocked by
- 01 (하네스 골격)
