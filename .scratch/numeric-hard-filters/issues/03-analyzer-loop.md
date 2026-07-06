# 이슈 03: 분석기 필터 추출 + 루프 배선 + 필터-범인 감지

Status: done
Type: AFK
Parent: .scratch/numeric-hard-filters/PRD.md

## What to build

분석기가 질의에서 숫자 제약을 뽑고, 추천 루프가 이를 하드 필터로 적용하며, 과제약 0건이면
필터가 범인인지 감지해 구체적으로 안내한다.

- **QueryAnalyzer**: `Analysis`에 `filters` 추가. 프롬프트에 레지스트리 스키마 주입(각 필터 범위·
  단위·storage 온도매핑) → "3000만원 이하"→`price_max=30000000`, "순도 99% 이상"→`purity_min=99`,
  "냉장/2~8도"→`storage_temp={min:2,max:8}`. 제약 없으면 `filters={}`. reformulate엔 필터 없음.
- **RagRecommender**: analyze의 filters를 retrieve에 전달, **루프 내내 유지**(재정식화는 검색어만).
  - **필터-범인 감지**: 필터 걸고 후보 0 → **필터 빼고 1회 더 retrieve** → 결과 있으면 검색어 재시도
    대신 구체적 안내("그 조건에 맞는 상품을 찾지 못했습니다") + result([]); 빼도 0이면 기존 재정식화.
- 필터가 하드임(자동 완화·소프트 없음).

## Acceptance criteria

- [ ] analyze: "3000만원 이하 원심분리기" → filters.price_max + 검색어; 제약 없으면 filters 빔
- [ ] 추천이 retrieve에 filters 전달, 재정식화 후에도 filters 유지
- [ ] 필터-범인: 필터 0·무필터 >0 → 구체적 안내 + result([]) (검색어 재시도 안 함)
- [ ] 필터·무필터 모두 0 → 기존 재정식화 루프
- [ ] 숫자 제약 없는 질의는 기존과 동일(회귀 없음)
- [ ] 전체 스위트 그린

## Blocked by

- 이슈 02 (필터 검색)
