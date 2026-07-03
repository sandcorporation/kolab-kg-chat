# 01 — ProductEnricher: 추천 카드에 URL·이미지·grounding 부착

Status: done — `apps/agent/enricher.py`(+ store.py에 image_url), 테스트 `tests/test_product_enricher.py` 통과.

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

추천 상품 id 집합에 대해 시스템이 결정적으로 **URL·썸네일·grounding**을 부착해 카드 페이로드를 만든다. LLM은 관여하지 않는다(환각 차단, ADR-0001). recommendation 페이로드를 확장한다:
`{ source_id, name, url, image_url, grounding:[{name,value,provenance}] }`.

- `url = https://www.kolabshop.com/shop/item.php?it_id={source_id}`
- `image_url` = 그래프/커넥터의 정규화된 첫 갤러리 이미지(it_img1); 없으면 null
- `grounding` = 그래프의 Product 속성(name/value/provenance)

## Acceptance criteria

- [ ] 주어진 source_id 목록 → 각 상품에 정확한 kolab URL 부착
- [ ] image_url이 정규화된 첫 이미지(없으면 null)로 채워짐
- [ ] grounding이 그래프 속성에서 채워짐
- [ ] 존재하지 않는 id는 결과에서 제외(또는 스킵)
- [ ] 결정적 단위/통합 테스트(그래프 시드 대상)

## Blocked by
None - can start immediately
