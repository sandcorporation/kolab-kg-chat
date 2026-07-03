"""비-Sigma 100 + Sigma 100에 구조(field_info) + Vision(캐시) 적재.

Vision은 이미지별로 캐시(vision_cache 테이블 + JSON) — 재실행 시 히트로 비용 0.
    docker compose run --rm \
      -e SOURCE_DB_HOST=real-source-db -e SOURCE_DB_USER=root -e SOURCE_DB_PASSWORD=root \
      -e SOURCE_DB_NAME=kolabshop -e OPENAI_VISION_MODEL=gpt-4o-mini \
      api python run_vision_cached.py 100
"""
import asyncio
import json
import os
import sys
from dataclasses import asdict

import aiomysql
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.agent.openai_client import OpenAIVisionClient, get_usage, reset_usage  # noqa: E402
from apps.agent.vision_cache import VisionCache, fetch_image_data_uri  # noqa: E402
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector  # noqa: E402
from apps.extraction.field_info import field_info_attributes  # noqa: E402
from apps.extraction.images import triage_spec_images  # noqa: E402
from apps.graph.store import GraphStore  # noqa: E402

VISION_PROMPT = (
    '이 실험장비/시약 이미지(스펙표·라벨·도면)에서 스펙을 추출하라. '
    'JSON {"attributes":[{"name","value"}]} 만 출력. 스펙이 없으면 빈 배열.'
)


async def select_ids(kind: str, limit: int) -> list[str]:
    conn = await aiomysql.connect(
        host=os.environ["SOURCE_DB_HOST"], port=int(os.environ.get("SOURCE_DB_PORT", "3306")),
        user=os.environ["SOURCE_DB_USER"], password=os.environ["SOURCE_DB_PASSWORD"],
        db=os.environ["SOURCE_DB_NAME"], charset="utf8mb4",
    )
    try:
        async with conn.cursor() as cur:
            if kind == "sigma":
                sql = ("SELECT it_id FROM g5_shop_item WHERE it_use=1 "
                       "AND it_img1 LIKE '%%sigmaaldrich%%' AND it_img1 NOT LIKE '%%no-image%%' LIMIT %s")
            else:
                sql = ("SELECT it_id FROM g5_shop_item WHERE it_use=1 "
                       "AND it_img1<>'' AND it_img1 NOT LIKE 'http%%' LIMIT %s")
            await cur.execute(sql, (limit,))
            return [r[0] for r in await cur.fetchall()]
    finally:
        conn.close()


async def run(limit: int):
    connector = YoungcartMySQLConnector.from_env()
    store = GraphStore()
    vision = OpenAIVisionClient()
    cache = VisionCache()
    reset_usage()

    stats = {"products": 0, "cache_hit": 0, "vision_call": 0, "fetch_fail": 0,
             "vision_fail": 0, "structured_variants": 0, "vision_attrs": 0}

    for kind in ("nonsigma", "sigma"):
        for source_id in await select_ids(kind, limit):
            doc = await connector.assemble(source_id)
            if doc is None:
                continue
            stats["products"] += 1
            await store.upsert_product(doc)

            # 구조(field_info) → Variant 속성 (무료)
            for v in doc.variants:
                fi = v.raw.get("field_info")
                if fi:
                    attrs = field_info_attributes(fi)
                    if attrs:
                        await store.set_variant_attributes(v.variant_key, [asdict(a) for a in attrs])
                        stats["structured_variants"] += 1

            # Vision(이미지별 캐시)
            product_vision_attrs = []
            for img in triage_spec_images(doc.images):
                cached = await cache.get(img.url)
                if cached is not None:
                    stats["cache_hit"] += 1
                    raw = cached
                else:
                    try:
                        data_uri = await fetch_image_data_uri(img.url)
                    except Exception:  # noqa: BLE001
                        stats["fetch_fail"] += 1
                        continue
                    try:
                        raw = await vision.extract([data_uri], VISION_PROMPT)
                        stats["vision_call"] += 1
                    except Exception:  # noqa: BLE001
                        stats["vision_fail"] += 1
                        continue
                    attrs = json.loads(raw).get("attributes", []) if raw else []
                    await cache.put(img.url, source_id, vision.model_version, raw, attrs)
                product_vision_attrs += json.loads(raw).get("attributes", []) if raw else []

            if product_vision_attrs:
                await store.set_attributes(source_id, [
                    {"name": a.get("name"), "value": a.get("value"), "provenance": "llm_ocr",
                     "confidence": 1.0, "is_candidate": False}
                    for a in product_vision_attrs if a.get("name")
                ])
                stats["vision_attrs"] += len(product_vision_attrs)

    u = get_usage()
    print("=== VISION+STRUCTURED RUN ===")
    print(stats)
    print(f"vision tokens chat_in={u['chat_in']} chat_out={u['chat_out']}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
