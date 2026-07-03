"""ProductEnricher (이슈 01) — 추천 상품 id에 URL·이미지·grounding을 결정적으로 부착.

LLM은 관여하지 않는다(환각 차단, ADR-0001). URL은 it_id로 결정적 생성.
"""
from __future__ import annotations

KOLAB_ITEM_URL = "https://www.kolabshop.com/shop/item.php?it_id={}"


class ProductEnricher:
    def __init__(self, store):
        self._store = store

    async def enrich(self, source_ids: list[str]) -> list[dict]:
        cards: list[dict] = []
        for source_id in source_ids:
            product = await self._store.get_product(source_id)
            if product is None:
                continue  # 존재하지 않는 id는 제외
            attrs = await self._store.get_attributes(source_id)
            price_min, price_max = await self._store.price_range(source_id)
            cards.append({
                "source_id": source_id,
                "name": product["name"],
                "url": KOLAB_ITEM_URL.format(source_id),
                "image_url": product.get("image_url") or None,
                "price_min": price_min,
                "price_max": price_max,
                "grounding": [
                    {"name": a["name"], "value": a["value"], "provenance": a["provenance"]}
                    for a in attrs
                ],
            })
        return cards
