"""이슈 10/03 — ImageTriage(실 URL: explan + 갤러리 앞 N) + 비전 속성 추출."""
import json

from apps.connectors.base import SourceImage
from apps.extraction.images import (
    FakeVisionClient,
    ImageAttributeExtractor,
    triage_spec_images,
)


def _gallery(n):
    return [SourceImage(f"/data/g{i}.jpg", i, "gallery") for i in range(1, n + 1)]


# ── 이슈 03: 트리아지 ──
def test_triage_selects_explan_and_first_n_gallery():
    images = _gallery(3) + [SourceImage("/data/explan1.jpg", 4, "explan")]
    selected = {i.url for i in triage_spec_images(images, gallery_limit=2)}
    assert "/data/explan1.jpg" in selected          # explan 우선
    assert "/data/g1.jpg" in selected and "/data/g2.jpg" in selected  # 갤러리 앞 2
    assert "/data/g3.jpg" not in selected            # 상한 초과 제외


def test_triage_empty_when_no_images():
    assert triage_spec_images([]) == []


# ── 비전 추출 ──
async def test_vision_extracts_attributes_tagged_llm_ocr():
    vision = FakeVisionClient(json.dumps({
        "attributes": [{"name": "measurement_range", "value": "1-1000 mPa·s", "confidence": 0.8}],
    }))
    result = await ImageAttributeExtractor(vision).extract("electronic_instrument", _gallery(3))
    assert result.attributes[0].name == "measurement_range"
    assert result.attributes[0].provenance == "llm_ocr"


async def test_no_images_skips_vision_call():
    vision = FakeVisionClient("{}")
    result = await ImageAttributeExtractor(vision).extract("reagent_chemical", [])
    assert result.attributes == []
    assert vision.last is None  # 이미지 없음 → 비전 호출 안 함


async def test_skips_attribute_already_known_from_text():
    vision = FakeVisionClient(json.dumps({
        "attributes": [
            {"name": "measurement_range", "value": "x"},
            {"name": "accuracy", "value": "±1%"},
        ],
    }))
    result = await ImageAttributeExtractor(vision).extract(
        "electronic_instrument", _gallery(2), known_names=frozenset({"measurement_range"})
    )
    assert {a.name for a in result.attributes} == {"accuracy"}
