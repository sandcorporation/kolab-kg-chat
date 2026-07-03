# 03 — Mock Source DB (영카트 스키마 + 시드)

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

kolabshop의 소스 DB를 흉내 내는 MySQL 컨테이너. **영카트(그누보드) 스키마**의 핵심 부분집합 — `g5_shop_item`(it_id PK, it_name, it_maker, ca_id, it_price, it_basic, it_explan, it_img1~N), `g5_shop_item_option`(it_id, io_id=옵션라벨, io_price=가격 delta, io_no), `g5_shop_category`(계층 ca_id) — 을 만들고, 실제 상품 4종을 시드한다: 메스플라스크(ISOLAB, 용량 19변형/텍스트 스펙), 점도계 VISCO B(ATAGO, 이미지 스펙, 구성 변형), PIPET PRO(색상 3변형=동일가/cosmetic), 중수소수 D₂O(CIL, CAS 7789-20-0, 포장 5변형).

월요일 실제 DB 교체 비용을 줄이려 스키마를 영카트에 충실히 맞춘다. 가격은 영카트식 `it_price + io_price`(delta)로 저장한다.

## Acceptance criteria

- [ ] docker-compose에 MySQL `source-db` 서비스 + init SQL(schema + seed) 마운트
- [ ] `g5_shop_item`/`g5_shop_item_option`/`g5_shop_category` 테이블 생성
- [ ] 4종 상품 + 변형(색상 3, 용량 19, 구성 N, 포장 5) + 카테고리 계층 시드
- [ ] 컨테이너 기동 후 smoke 쿼리로 4종 상품과 변형 수가 조회됨
- [ ] 이미지 컬럼: 점도계는 다중(스펙 이미지 포함), 나머지는 단일

## Blocked by

- `01-walking-skeleton.md`
