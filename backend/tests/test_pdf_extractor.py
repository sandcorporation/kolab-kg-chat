"""이슈 01 — PdfTextExtractor: URL → PDF 텍스트(fetch 주입, 폴백)."""
from pathlib import Path

from apps.extraction.pdf import PdfTextExtractor

FIXTURE = Path(__file__).parent / "fixtures" / "sample_spec.pdf"


def _fetch_returning(content: bytes, content_type: str):
    async def fetch(url):
        return content, content_type
    return fetch


def _fetch_raising():
    async def fetch(url):
        raise RuntimeError("boom")
    return fetch


async def test_extract_parses_pdf_text():
    pdf = FIXTURE.read_bytes()
    text = await PdfTextExtractor(_fetch_returning(pdf, "application/pdf")).extract("http://x/spec.pdf")
    assert "borosilicate" in text.lower()
    assert "flask" in text.lower()


async def test_extract_rejects_non_pdf_content_type():
    ex = PdfTextExtractor(_fetch_returning(b"<html>nope</html>", "text/html"))
    assert await ex.extract("http://x/page.html") == ""


async def test_extract_swallows_fetch_failure():
    assert await PdfTextExtractor(_fetch_raising()).extract("http://x/spec.pdf") == ""


async def test_extract_trims_to_max_chars():
    pdf = FIXTURE.read_bytes()
    ex = PdfTextExtractor(_fetch_returning(pdf, "application/pdf"), max_chars=20)
    text = await ex.extract("http://x/spec.pdf")
    assert 0 < len(text) <= 20


async def test_extract_rejects_oversized_pdf():
    pdf = FIXTURE.read_bytes()
    ex = PdfTextExtractor(_fetch_returning(pdf, "application/pdf"), max_bytes=10)
    assert await ex.extract("http://x/spec.pdf") == ""


async def test_extract_empty_url_returns_empty():
    assert await PdfTextExtractor(_fetch_raising()).extract("") == ""


def test_build_pdf_extractor_returns_operational_extractor():
    from apps.extraction.pdf import build_pdf_extractor

    assert isinstance(build_pdf_extractor(), PdfTextExtractor)  # httpx 어댑터로 구성됨
