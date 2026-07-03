-- kolabshop 실제 덤프(영카트, MariaDB) 스키마의 충실한 부분집합 (이슈 26 fixture 재정렬).
-- 실제 덤프엔 카테고리 이름 테이블이 없다 → 여기도 두지 않는다.
SET NAMES utf8mb4;

CREATE TABLE g5_shop_item (
  it_id    VARCHAR(20)  NOT NULL PRIMARY KEY,
  ca_id    VARCHAR(10)  NOT NULL DEFAULT '',
  ca_id2   VARCHAR(10)  DEFAULT NULL,
  ca_id3   VARCHAR(10)  DEFAULT NULL,
  it_name  VARCHAR(511) NOT NULL DEFAULT '',
  it_brand VARCHAR(255) NOT NULL DEFAULT '',
  it_maker VARCHAR(255) NOT NULL DEFAULT '',
  it_price INT          NOT NULL DEFAULT 0,
  it_basic TEXT,
  it_explan MEDIUMTEXT,
  it_img1  VARCHAR(510) NOT NULL DEFAULT '',
  it_img2  VARCHAR(255) NOT NULL DEFAULT '',
  it_img3  VARCHAR(255) NOT NULL DEFAULT '',
  it_img4  VARCHAR(255) NOT NULL DEFAULT '',
  it_img5  VARCHAR(255) NOT NULL DEFAULT '',
  it_use   TINYINT      NOT NULL DEFAULT 1,
  it_time        DATETIME DEFAULT NULL,  -- 등록일시(그누보드5)
  it_update_time DATETIME DEFAULT NULL   -- 수정일시(증분 동기화 기준, 이슈 05)
) DEFAULT CHARSET=utf8mb4;

-- 실제 옵션: io_catno(카탈로그), io_description(스펙 라벨), io_price(절대가)
CREATE TABLE g5_shop_item_option (
  io_no          INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
  it_id          VARCHAR(20)  NOT NULL,
  io_id          VARCHAR(255) NOT NULL DEFAULT '',
  io_type        TINYINT      NOT NULL DEFAULT 0,
  io_catno       VARCHAR(255) NOT NULL DEFAULT '',
  io_model       VARCHAR(255) NOT NULL DEFAULT '',
  io_description VARCHAR(511) NOT NULL DEFAULT '',
  io_unit        VARCHAR(255) NOT NULL DEFAULT '',
  io_price       INT          NOT NULL DEFAULT 0,
  io_use         TINYINT      NOT NULL DEFAULT 1,
  KEY idx_option_it (it_id)
) DEFAULT CHARSET=utf8mb4;
