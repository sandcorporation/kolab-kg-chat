"""데모 시드 — 4종 상품 + (결정적) 속성 + 호환 엣지를 기본 그래프 'kg'에 적재.

OpenAI 없이 위젯에서 추천을 시연하기 위한 것. 속성은 LLM이 아니라 하드코딩(데모)이라
provenance=structured 로 둔다. 멱등하므로 여러 번 실행해도 안전하다.

    docker compose run --rm api python seed_demo.py
"""
import asyncio
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.connectors.youngcart_mysql import YoungcartMySQLConnector  # noqa: E402
from apps.graph.store import GraphStore  # noqa: E402

ATTRS = {
    "1548728629": [("material", "glass_borosilicate"), ("grade", "class_A"), ("autoclavable", True)],
    "DLM-4": [("purity_percent", 99.9), ("cas_number", "7789-20-0"), ("storage_condition", "room_temp")],
    "1712107033": [("power_source", "rechargeable")],
    "1667982841": [("measurement_range", "1-1000 mPa·s"), ("accuracy", "±1%"), ("power_source", "ac_adapter")],
}


async def seed():
    connector = YoungcartMySQLConnector.from_env()
    store = GraphStore()
    async for source_id in connector.iter_product_ids():
        doc = await connector.assemble(source_id)
        await store.upsert_product(doc)
        attrs = [
            {"name": n, "value": v, "provenance": "structured", "confidence": 1.0, "is_candidate": False}
            for n, v in ATTRS.get(source_id, [])
        ]
        if attrs:
            await store.set_attributes(source_id, attrs)
    await store.add_compatibility("1667982841", "DLM-4")  # 점도계 ↔ 표준액(예시)
    print("demo seeded: 4 products + attributes + compatibility")


if __name__ == "__main__":
    asyncio.run(seed())
