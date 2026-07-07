"""이슈 03 — Mock Source DB(영카트) 스모크.

소스 MySQL이 떠 있고 4종 상품 + 변형이 시드됐는지 확인한다.
"""
import os

import aiomysql


async def _connect():
    return await aiomysql.connect(
        host=os.environ["SOURCE_DB_HOST"],
        port=int(os.environ.get("SOURCE_DB_PORT", "3306")),
        user=os.environ["SOURCE_DB_USER"],
        password=os.environ["SOURCE_DB_PASSWORD"],
        db=os.environ["SOURCE_DB_NAME"],
        charset="utf8mb4",
    )


async def test_seed_has_four_products():
    # 판매 상품 4종(품절 it_soldout=1 픽스처는 별도 — 적재 대상 아님).
    conn = await _connect()
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM g5_shop_item WHERE it_soldout = 0")
            (n,) = await cur.fetchone()
            assert n == 4
    finally:
        conn.close()


async def test_variant_counts_per_product():
    expected = {  # 변형 = io_type=0(부가옵션 io_type=1 제외). flask엔 교정성적서 add-on 1개 있음.
        "1712107033": 3,    # PIPET PRO 색상
        "1548728629": 19,   # 메스플라스크 용량
        "1667982841": 2,    # 점도계 구성
        "DLM-4": 5,         # 중수소수 포장
    }
    conn = await _connect()
    try:
        async with conn.cursor() as cur:
            for it_id, count in expected.items():
                await cur.execute(
                    "SELECT COUNT(*) FROM g5_shop_item_option "
                    "WHERE it_id = %s AND io_type = 0 AND io_stock_qty > 0",
                    (it_id,),
                )
                (n,) = await cur.fetchone()
                assert n == count, f"{it_id}: expected {count}, got {n}"
    finally:
        conn.close()


async def test_viscometer_has_spec_images():
    """점도계는 스펙 이미지 다중 보유(OCR 경로용)."""
    conn = await _connect()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT it_img2, it_img3 FROM g5_shop_item WHERE it_id = %s", ("1667982841",)
            )
            img2, img3 = await cur.fetchone()
            assert img2 and img3
    finally:
        conn.close()
