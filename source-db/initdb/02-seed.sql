-- 실제 스키마로 재표현한 4종 테스트 상품 (이슈 26 fixture). io_price는 절대가.
SET NAMES utf8mb4;

INSERT INTO g5_shop_item
  (it_id, ca_id, ca_id2, it_name, it_brand, it_price, it_basic, it_explan, it_img1, it_img2, it_img3, it_img4, it_use) VALUES
  ('1712107033', '30', '3020', 'Lab Touch PIPET PRO 전동 피펫 에이드', '고려에이스과학', 288750,
   '전동 피펫 에이드, 거치대 2종 포함', '<p>충전식 전동 피펫 에이드.</p>',
   'https://img.test/pipetpro/main.jpg', '', '', '', 1),
  ('1548728629', '20', '2010', 'Volumetric Flask Clear class A / 투명A급 메스플라스크', 'ISOLAB', 0,
   '재질 붕규산 유리 Class A',
   '<p>재질: 투명 붕규산 유리(borosilicate). 등급: Class A.</p><img src="https://img.test/flask/spec-explan.jpg">',
   'https://img.test/flask/main.jpg', '', '', '', 1),
  ('1667982841', '30', '3010', 'Digital Viscometer VISCO B (L)', 'ATAGO', 3630000,
   '디지털 점도계. 상세 사양은 이미지 참조.', '<p>ATAGO 디지털 점도계. 스펙은 이미지 참조.</p>',
   'https://img.test/visco/main.jpg', 'https://img.test/visco/spec1.jpg', 'https://img.test/visco/spec2.jpg', 'https://img.test/visco/dim.jpg', 1),
  ('DLM-4', '40', '4010', 'Deuterium oxide (D, 99.9%) 중수소수', 'CIL', 64460,
   '중수소수 D2O 순도 99.9% CAS 7789-20-0', '<p>Deuterium oxide. D 99.9%. CAS 7789-20-0.</p>',
   'https://img.test/d2o/main.jpg', '', '', '', 1);

-- 품절 아이템(it_soldout=1) — 적재 id 선택(iter/sample/changed_since)이 걸러야 한다.
INSERT INTO g5_shop_item
  (it_id, ca_id, ca_id2, it_name, it_brand, it_price, it_basic, it_use, it_soldout) VALUES
  ('SOLD-1', '20', '2010', '품절 상품 테스트', 'TESTBRAND', 10000, '품절 테스트', 1, 1);

-- 증분 동기화 기준선(모든 상품 동일 baseline). 테스트는 특정 상품의 it_update_time을 올린다.
UPDATE g5_shop_item SET it_time = '2026-01-01 00:00:00', it_update_time = '2026-01-01 00:00:00';

-- PIPET PRO 색상 3 (cosmetic, 절대가 동일)
INSERT INTO g5_shop_item_option (it_id, io_id, io_catno, io_description, io_unit, io_price) VALUES
  ('1712107033', '1', 'KA.33-62N', '블루', 'EA', 288750),
  ('1712107033', '2', 'KA.33-63N', '그레이', 'EA', 288750),
  ('1712107033', '3', 'KA.33-64N', '오렌지', 'EA', 288750);

-- 메스플라스크 용량 19 (functional, io_price 절대가)
INSERT INTO g5_shop_item_option (it_id, io_id, io_catno, io_description, io_unit, io_price) VALUES
  ('1548728629', '1', '013.01.005', '5ml, NS 10/19', 'EA', 13400),
  ('1548728629', '2', '013.01.010', '10ml, NS 10/19', 'EA', 13400),
  ('1548728629', '3', '013.01.020', '20ml, NS 10/19', 'EA', 14200),
  ('1548728629', '4', '013.01.025', '25ml, NS 10/19', 'EA', 14200),
  ('1548728629', '5', '013.01.026', '25ml, NS 12/21', 'EA', 16300),
  ('1548728629', '6', '013.01.050', '50ml, NS 12/21', 'EA', 15800),
  ('1548728629', '7', '013.01.051', '50ml, NS 14/23', 'EA', 18500),
  ('1548728629', '8', '013.01.100', '100ml, NS 12/21', 'EA', 16900),
  ('1548728629', '9', '013.01.101', '100ml, NS 14/23', 'EA', 19400),
  ('1548728629', '10', '013.01.150', '150ml, NS 14/23', 'EA', 33700),
  ('1548728629', '11', '013.01.200', '200ml, NS 14/23', 'EA', 24300),
  ('1548728629', '12', '013.01.250', '250ml, NS 14/23', 'EA', 25600),
  ('1548728629', '13', '013.01.300', '300ml, NS 14/23', 'EA', 38600),
  ('1548728629', '14', '013.01.400', '400ml, NS 19/26', 'EA', 44300),
  ('1548728629', '15', '013.01.500', '500ml, NS 19/26', 'EA', 32900),
  ('1548728629', '16', '013.01.901', '1000ml, NS 24/29', 'EA', 46700),
  ('1548728629', '17', '013.01.902', '2000ml, NS 29/32', 'EA', 79900),
  ('1548728629', '18', '013.01.905', '5000ml, NS 34/35', 'EA', 257500),
  ('1548728629', '19', '013.01.910', '10000ml, NS 45/40', 'EA', 435900);

-- 부가옵션(io_type=1, 교정성적서) — io_type=0 필터로 변형·최저가에서 제외되어야 함
-- (실사례 1515660121: 성적서 5만원이 최저가로 튀던 버그 재현). 최저가는 13400이어야.
INSERT INTO g5_shop_item_option (it_id, io_id, io_catno, io_description, io_unit, io_price, io_type) VALUES
  ('1548728629', '90', 'CAL-CERT', '교정성적서 질량 교정', 'EA', 5000, 1);

-- 품절 옵션(io_type=0, io_stock_qty=0) — io_stock_qty>0 필터로 변형·최저가에서 제외되어야 함
-- (실사례 1515569969 AD-720Di 프린터 품절). 8000<13400이라 제외 안 하면 최저가로 튐.
INSERT INTO g5_shop_item_option (it_id, io_id, io_catno, io_description, io_unit, io_price, io_stock_qty) VALUES
  ('1548728629', '91', 'SOLDOUT-VAR', '품절 변형', 'EA', 8000, 0);

-- 점도계 구성 2 (functional)
INSERT INTO g5_shop_item_option (it_id, io_id, io_catno, io_description, io_unit, io_price) VALUES
  ('1667982841', '1', 'ATAGO6840', 'VISCO B (L) 본체', 'EA', 3630000),
  ('1667982841', '2', 'ATAGO6865', 'Package E - 항온 세트 포함', 'EA', 6182000);

-- 중수소수 포장 5 (functional)
INSERT INTO g5_shop_item_option (it_id, io_id, io_catno, io_description, io_unit, io_price) VALUES
  ('DLM-4', '1', 'DLM-4-10x0.7', '10 x 0.7g', 'EA', 64460),
  ('DLM-4', '2', 'DLM-4-10x1', '10 x 1g', 'EA', 107140),
  ('DLM-4', '3', 'DLM-4-25', '25g', 'EA', 124520),
  ('DLM-4', '4', 'DLM-4-100', '100g', 'EA', 427900),
  ('DLM-4', '5', 'DLM-4-10x100', '10 x 100g', 'EA', 4150630);
