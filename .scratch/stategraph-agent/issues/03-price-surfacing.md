# 이슈 03: 가격 노출 (변형 가격 범위)

Status: done — store.price_range(변형 min/max, null 제외), enricher price_min/max, ProductCard 필드+Orval, 카드 ₩범위/단일가 표시(없으면 생략). 단위 5 + 라이브(7카드 ₩302,280 등).
Type: AFK
Parent: .scratch/stategraph-agent/PRD.md

## What to build

상품의 변형(Variant) 가격을 집계해 **카드에 가격 범위**를 노출한다. 그래프 store에 상품의 변형 가격 최저·최고를 구하는 조회(**PriceRange 집계기**, `HAS_VARIANT` 중 `price IS NOT NULL`만)를 추가하고, 엔리처가 카드에 `price_min`/`price_max`를 채운다. `ProductCard` 스키마에 두 필드를 더하고, 프론트 카드가 `min==max`면 단일가·아니면 "₩12,000~₩45,000"를 표기하며 가격이 없으면 줄을 생략한다. Orval 재생성으로 타입 반영.

## Acceptance criteria

- [ ] store 가격 조회: 변형 여러 개면 (min,max), 가격 없는 변형 제외, 전부 없으면 (None,None)
- [ ] 엔리처가 카드에 price_min/price_max 부착(없으면 None)
- [ ] `ProductCard`에 price_min·price_max 추가, Orval 타입 재생성
- [ ] 프론트 카드가 가격 범위/단일가 표기, 가격 없으면 생략(억지 표기 금지)
- [ ] 가격 집계 단위 테스트 + SSE 카드에 price 필드 포함 검증

## Blocked by

None - can start immediately (에이전트 내부와 독립)
