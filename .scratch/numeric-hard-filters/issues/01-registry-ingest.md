# 이슈 01: 필터 레지스트리 + 파서 + kg_embedding 컬럼 + 적재 저장

Status: done
Type: AFK
Parent: .scratch/numeric-hard-filters/PRD.md

## What to build

숫자 범위 필터를 선언적 레지스트리로 정의하고, 상품 doc에서 값을 추출·정규화해 kg_embedding
숫자 컬럼(min/max)에 색인한다.

- **레지스트리**: 각 필터 = (이름, source 추출, parse). v1 = price·purity·molecular_weight·storage_temp.
  - price: 변형 io_price의 min/max(이미 숫자).
  - purity·molecular_weight: field_info 텍스트에서 숫자 추출(">=99.5%"→99.5, "71.08"→71.08).
  - storage_temp: 소어휘 매핑("2-8C"→(2,8), "room"→(15,25), "-20"→(-20,-20)). point→min=max.
- **FilterExtractor**: `extract(doc) -> {name: (min,max)}`. 파싱 실패·값 없음 → 그 필터 생략(NULL).
- **스키마**: kg_embedding에 필터별 `_min`·`_max` 숫자 컬럼 추가(기존 행 NULL 허용).
- **적재 저장**: embed_product(또는 러너)가 추출값을 그 컬럼에 함께 저장. content_hash 무관(값이
  이미 해시에 반영된 데이터에서 나옴).

## Acceptance criteria

- [ ] 파서: "2-8C"→(2,8), ">=99.5% (GC)"→순도 99.5, "82-86 C"→(82,86), "71.08"→(71.08,71.08), "room temperature"→(15,25)
- [ ] FilterExtractor: 페이크 doc → 필터별 (min,max); 값 없으면 생략
- [ ] kg_embedding에 price_min/max·purity_min/max·molecular_weight_min/max·storage_temp_min/max 컬럼
- [ ] embed_product가 필터값을 저장(적재 후 컬럼 채워짐)
- [ ] 값 없는 필터는 NULL
- [ ] 전체 스위트 그린

## Blocked by

- None - can start immediately
