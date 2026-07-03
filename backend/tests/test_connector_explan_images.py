"""이슈 01 — 커넥터가 it_explan의 <img>를 이미지로 캡처(갤러리와 병합·중복제거)."""
from apps.connectors.youngcart_mysql import (
    YoungcartMySQLConnector,
    extract_img_srcs,
    normalize_image_url,
)


def test_normalize_image_url():
    assert normalize_image_url("https://x/y.jpg") == "https://x/y.jpg"
    assert normalize_image_url("abc/1.jpg") == "https://www.kolabshop.com/data/item/abc/1.jpg"
    assert normalize_image_url("https://cdn/pdp-no-image_w640.png") is None  # 플레이스홀더 스킵
    assert normalize_image_url("") is None


def test_extract_img_srcs_parses_html():
    html = '<p>스펙</p><img src="https://cdn/spec1.jpg"><img src=\'https://cdn/spec2.jpg\'/>'
    assert extract_img_srcs(html) == ["https://cdn/spec1.jpg", "https://cdn/spec2.jpg"]


def test_extract_img_srcs_empty():
    assert extract_img_srcs("") == []
    assert extract_img_srcs(None) == []
    assert extract_img_srcs("<p>no image</p>") == []


async def test_assemble_includes_explan_images_deduped():
    doc = await YoungcartMySQLConnector.from_env().assemble("1548728629")
    urls = [i.url for i in doc.images]
    assert "https://img.test/flask/main.jpg" in urls          # 갤러리
    assert "https://img.test/flask/spec-explan.jpg" in urls   # explan 임베디드
    assert len(urls) == len(set(urls))                  # 중복 제거
    # description_text는 여전히 태그 제거 텍스트
    assert "<img" not in doc.description_text
