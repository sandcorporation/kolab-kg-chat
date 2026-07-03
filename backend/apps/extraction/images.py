"""ImageTriage + 비전 LLM 속성 추출 (이슈 10, ADR-0005).

스펙/도면 이미지만 선별(비용 통제)해 비전 LLM이 직접 읽어 속성을 추출한다(고전 OCR 아님).
이미지 유래 속성은 provenance=llm_ocr로 태깅한다.
"""
from __future__ import annotations

import json
from typing import Protocol

from apps.extraction.extractor import (
    ExtractedAttribute,
    ExtractionResult,
    coerce_confidence,
)
from apps.extraction.vocabulary import attributes_for, is_controlled

DEFAULT_GALLERY_LIMIT = 2


def triage_spec_images(images, gallery_limit: int = DEFAULT_GALLERY_LIMIT) -> list:
    """비전 대상 선별 (이슈 03) — 실 URL엔 파일명 힌트가 없으므로:
    explan 임베디드 이미지(우선) + 갤러리 앞 N장. 전량 비전을 피해 비용을 통제한다.
    """
    explan = [img for img in images if img.source == "explan"]
    gallery = [img for img in images if img.source != "explan"][:gallery_limit]
    return explan + gallery


class VisionClient(Protocol):
    model_version: str

    async def extract(self, image_urls: list[str], prompt: str) -> str:
        ...


class FakeVisionClient:
    def __init__(self, response: str, model_version: str = "fake-vision-v1"):
        self._response = response
        self.model_version = model_version
        self.last: tuple | None = None

    async def extract(self, image_urls: list[str], prompt: str) -> str:
        self.last = (image_urls, prompt)
        return self._response


_PROMPT = "다음 이미지(스펙표/도면)에서 유형 '{ptype}'의 통제 어휘 속성을 추출하라. 허용: {attrs}. JSON {{\"attributes\":[{{\"name\",\"value\",\"confidence\"}}]}}만 출력."


class ImageAttributeExtractor:
    def __init__(self, vision):
        self._vision = vision

    async def extract(
        self, product_type: str, images, known_names: frozenset[str] = frozenset()
    ) -> ExtractionResult:
        spec_images = triage_spec_images(images)
        if not spec_images:
            return ExtractionResult(product_type=product_type, attributes=[])  # 비전 호출 생략

        prompt = _PROMPT.format(
            ptype=product_type, attrs=", ".join(attributes_for(product_type).keys())
        )
        raw = await self._vision.extract([i.url for i in spec_images], prompt)
        data = json.loads(raw)

        attributes = []
        for a in data.get("attributes", []):
            if a["name"] in known_names:
                continue  # 텍스트에서 이미 확정 → 생략
            attributes.append(
                ExtractedAttribute(
                    name=a["name"],
                    value=a["value"],
                    provenance="llm_ocr",
                    confidence=coerce_confidence(a.get("confidence", 1.0)),
                    is_candidate=not is_controlled(product_type, a["name"]),
                )
            )
        return ExtractionResult(product_type=product_type, attributes=attributes)
