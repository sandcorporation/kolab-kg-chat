"""Vision 강화 (이슈 03) — 이미지 유래(llm_ocr) 속성을 structured에 병합, per-product 캐시.

구조 스펙이 부족한 상품(이미지-only)에만 돌려 config 3이 config 2가 못 보던 스펙을
쓰게 한다. 캐시로 재실행 비용 0.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict

from apps.agent.vision_cache import fetch_image_data_uri


async def enrich_product_vision(store, doc, extractor, product_type: str) -> int:
    """doc의 이미지에서 vision 속성을 추출해 기존(structured) 속성에 병합한다."""
    existing = await store.get_attributes(doc.source_id)
    known = frozenset(a["name"] for a in existing)
    result = await extractor.extract(product_type, doc.images, known_names=known)
    vision_attrs = [asdict(a) for a in result.attributes]
    if vision_attrs:
        await store.set_attributes(doc.source_id, existing + vision_attrs)
    return len(vision_attrs)


class CachingVisionClient:
    """VisionClient를 감싸 (이미지들+프롬프트) 단위로 캐시하고, 이미지를 서버측에서 fetch한다.

    OpenAI가 kolabshop CDN을 직접 못 받는 경우가 있어 base64 data URI로 넘긴다.
    """

    def __init__(self, inner, cache, source_id: str, fetch_fn=fetch_image_data_uri):
        self._inner = inner
        self._cache = cache
        self._sid = source_id
        self._fetch = fetch_fn
        self.model_version = getattr(inner, "model_version", "vision")

    async def extract(self, image_urls: list[str], prompt: str) -> str:
        key = "vk:" + hashlib.sha256(("|".join(image_urls) + prompt).encode()).hexdigest()
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        uris = []
        for url in image_urls:
            try:
                uris.append(await self._fetch(url))
            except Exception:  # noqa: BLE001 — fetch 실패 이미지는 건너뜀(raw URL 폴백 금지)
                pass
        if not uris:
            # 모든 이미지 fetch 실패(예: Sigma CDN 차단) → vision 호출 생략, 빈 결과 캐시
            raw = '{"attributes": []}'
        else:
            raw = await self._inner.extract(uris, prompt)
        await self._cache.put(key, self._sid, self.model_version, raw, [])
        return raw
