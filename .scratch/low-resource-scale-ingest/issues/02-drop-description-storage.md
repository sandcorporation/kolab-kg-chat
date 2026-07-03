# 02 — Product 노드에서 description 저장 제거

Status: done

## Parent
`.scratch/low-resource-scale-ingest/PRD.md`

## What to build

`upsert_product`가 더 이상 `p.description`을 그래프에 저장하지 않는다(읽기 경로 미사용). `--llm` 추출은 그래프가 아니라 조립 시점 ProductDocument.description_text를 쓰므로 영향받지 않는다.

## Acceptance criteria

- [ ] 적재 후 Product 노드에 description 속성이 없다
- [ ] 이름·브랜드·카테고리·image_url·content_hash·속성은 그대로 저장/조회됨
- [ ] LLM 속성 추출(설명 텍스트 기반)이 여전히 동작

## Blocked by
None - can start immediately
