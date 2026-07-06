"""PdfTextExtractor (PDF 문서 강화) — URL → PDF 텍스트 딥모듈.

fetch·content-type 가드·크기 상한·pypdf 파싱·트림·폴백을 인터페이스 뒤에 은닉한다.
실패(비-PDF·타임아웃·깨진 PDF·빈 텍스트·초과 크기)는 전부 ""로 흡수해 적재를 막지 않는다.
fetch를 주입받아 네트워크 없이 테스트 가능하다(운영은 httpx 어댑터, 이슈 03).
"""
from __future__ import annotations

import asyncio
import io
import re

_MAX_BYTES = 10 * 1024 * 1024  # 10MB


class PdfTextExtractor:
    def __init__(self, fetch, max_chars: int = 6000, max_bytes: int = _MAX_BYTES):
        self._fetch = fetch          # async (url) -> (bytes, content_type)
        self._max_chars = max_chars
        self._max_bytes = max_bytes

    async def extract(self, url: str) -> str:
        if not url:
            return ""
        try:
            content, content_type = await self._fetch(url)
        except Exception:  # noqa: BLE001 — fetch 실패(타임아웃 등)는 적재를 막지 않는다
            return ""
        if "pdf" not in (content_type or "").lower():
            return ""  # 직접-PDF 아님(HTML 랜딩 등) → 스킵
        if not content or len(content) > self._max_bytes:
            return ""  # 빈 응답·초과 크기 방어
        try:
            text = await asyncio.to_thread(self._parse, content)
        except Exception:  # noqa: BLE001 — 깨진 PDF 등
            return ""
        text = re.sub(r"\s+", " ", text or "").strip()
        return text[: self._max_chars]

    @staticmethod
    def _parse(content: bytes) -> str:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages)


def build_pdf_extractor() -> PdfTextExtractor:
    """운영 PdfTextExtractor — httpx 스트리밍 fetch 어댑터.

    `PDF_HTTP_TIMEOUT`·`PDF_MAX_BYTES`(스트리밍 중 초과 시 조기 중단)·`PDF_MAX_CHARS`를 적용한다.
    """
    import os

    max_chars = int(os.environ.get("PDF_MAX_CHARS", "6000"))
    max_bytes = int(os.environ.get("PDF_MAX_BYTES", str(_MAX_BYTES)))
    timeout = float(os.environ.get("PDF_HTTP_TIMEOUT", "10"))

    async def fetch(url: str):
        import httpx

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:  # 초과 → 빈 바이트(extractor가 "" 반환)
                        return b"", content_type
                    chunks.append(chunk)
                return b"".join(chunks), content_type

    return PdfTextExtractor(fetch, max_chars=max_chars, max_bytes=max_bytes)
