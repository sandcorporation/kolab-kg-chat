# 00 — 실 데이터 적재 + EvalCorpus 선별

Status: done — EvalCorpus 모듈+build_eval_corpus 명령, 실 데이터 250개(structured 121·mixed 116·image_only 13) eval_graph 적재. 테스트 tests/test_eval_corpus.py.

## Parent
`.scratch/retrieval-quality-eval/PRD.md`

## What to build

실험의 0단계 전제. `real-source-db`(2.6GB 덤프)를 구조 적재해 별도 실험 그래프(예: `eval_graph`)를 만들고, **EvalCorpus 빌더**가 실 카탈로그에서 ~200-300 Product를 **계층 태그와 함께** 결정적으로 선별·영속한다. 태그: 차이를 드러낼 케이스를 의도적으로 포함 — 이미지-only(스펙이 이미지에만/field_info 희소), 한/영·유의어 미스매치, 모든 Product Type 망라.

## Acceptance criteria

- [ ] real-source-db 적재 후 실험 그래프에 구조(structured) 속성으로 상품이 들어간다
- [ ] EvalCorpus가 ~200-300 상품을 선별하고 각 상품에 계층 태그(image_only/semantic/structured/…)를 붙여 영속한다
- [ ] 선별은 시드 고정 시 재현 가능(결정적)
- [ ] 코퍼스에 이미지-only·한영 미스매치·모든 Product Type이 실제로 포함됨을 확인

## Blocked by
None - can start immediately (real-source-db 덤프가 있어야 함)
