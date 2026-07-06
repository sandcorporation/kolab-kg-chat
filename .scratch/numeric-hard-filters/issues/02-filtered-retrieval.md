# 이슈 02: 필터 검색 (WHERE 겹침, NULL 제외)

Status: done
Type: AFK
Parent: .scratch/numeric-hard-filters/PRD.md

## What to build

검색이 필터를 받아 SQL `WHERE`로 시맨틱·키워드와 동시에 건다(겹침 규칙).

- **EmbeddingStore.search(query, k, filters)**: 필터마다 `WHERE`:
  - 이하(max 제약 X): `col_min <= X`
  - 이상(min 제약 X): `col_max >= X`
  - 범위[A,B]: `col_min <= B AND col_max >= A`
  - 다중 필터는 AND. **컬럼 NULL이면 그 조건 불통과**(정보 없는 상품 제외).
- **keyword_search(query, limit, filters)**: 동일 필터 적용.
- **HybridRetriever.retrieve(keywords, semantic, filters)**: 필터를 두 검색에 전달.
- 필터 비면 기존 동작과 동일.

## Acceptance criteria

- [ ] price_max 필터: price_min<=X인 상품만
- [ ] purity_min 필터: purity_max>=X인 상품만
- [ ] 범위 필터(storage 2~8): col_min<=8 AND col_max>=2 겹침
- [ ] NULL 컬럼 상품은 해당 필터에서 제외
- [ ] 다중 필터 AND
- [ ] 필터 없으면 기존 검색 결과 불변
- [ ] 전체 스위트 그린

## Blocked by

- 이슈 01 (레지스트리·컬럼)
