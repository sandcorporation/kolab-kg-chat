"""ProductEnricher (ADR-0016) — 추천 상품 id에 URL·이미지·가격·grounding을 결정적으로 부착.

C(소스 하이드레이션): 상품 사실은 우리 DB에 복제하지 않고, 선택된 id만 소스 DB에서
배치 하이드레이션(커넥터.assemble_many, WHERE it_id IN … 인덱스 스캔)해 카드를 만든다.
grounding 속성은 하이드레이션한 문서에서 결정적 추출기로 뽑는다. LLM은 관여하지 않는다
(환각 차단, ADR-0001). URL은 it_id로 결정적 생성.
"""
from __future__ import annotations

KOLAB_ITEM_URL = "https://www.kolabshop.com/shop/item.php?it_id={}"


class ProductEnricher:
    def __init__(self, connector, extractor):
        self._connector = connector    # assemble_many(ids) → {source_id: ProductDocument}
        self._extractor = extractor    # extract(doc) → ExtractionResult(attributes)

    async def enrich(self, source_ids: list[str]) -> list[dict]:
        docs = await self._connector.assemble_many(source_ids)
        cards: list[dict] = []
        for source_id in source_ids:  # 추천 순서 보존
            doc = docs.get(source_id)
            if doc is None:
                continue  # 소스에 없는 id는 제외
            result = await self._extractor.extract(doc)
            prices = [v.price for v in (doc.variants or []) if v.price is not None]
            images = doc.images or []
            cards.append({
                "source_id": source_id,
                "name": doc.name,
                "url": KOLAB_ITEM_URL.format(source_id),
                "image_url": images[0].url if images else None,
                "price_min": min(prices) if prices else None,
                "price_max": max(prices) if prices else None,
                "grounding": [
                    {"name": a.name, "value": a.value, "provenance": a.provenance}
                    for a in result.attributes
                ],
            })
        return cards
