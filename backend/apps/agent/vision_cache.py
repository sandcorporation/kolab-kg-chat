"""Vision 결과 캐시 (이슈: 사용자 OCR 열람용).

이미지 URL 키로 Postgres `public.vision_cache` 테이블 + JSON 파일에 원본 응답을 저장한다.
DB 클라이언트로 바로 SELECT해 이미지별 OCR 원본을 확인할 수 있고, 재실행 시 캐시
히트로 비용 0(= content-hash 게이팅 역할).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

import httpx

from apps.core.db import connect

JSON_DIR = Path(os.environ.get("VISION_JSON_DIR", "/app/vision_out"))


async def fetch_image_data_uri(url: str, timeout: float = 12.0) -> str:
    """이미지를 서버측에서 받아 base64 data URI로 변환(OpenAI 직접 fetch 실패 회피)."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        b64 = base64.b64encode(resp.content).decode("ascii")
        return f"data:{content_type};base64,{b64}"


class VisionCache:
    def __init__(self, connect_factory=connect, json_dir: Path = JSON_DIR):
        self._connect = connect_factory
        self._json_dir = json_dir

    async def _ensure_table(self, cur) -> None:
        await cur.execute(
            "CREATE TABLE IF NOT EXISTS public.vision_cache ("
            " image_url text PRIMARY KEY,"
            " source_id text,"
            " model text,"
            " raw_response text,"
            " extracted_attrs jsonb,"
            " created_at timestamptz DEFAULT now())"
        )

    async def get(self, image_url: str) -> str | None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure_table(cur)
                await cur.execute(
                    "SELECT raw_response FROM public.vision_cache WHERE image_url = %s", (image_url,)
                )
                row = await cur.fetchone()
        finally:
            await conn.close()
        return row[0] if row else None

    async def put(
        self, image_url: str, source_id: str, model: str, raw_response: str, extracted_attrs: list
    ) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure_table(cur)
                await cur.execute(
                    "INSERT INTO public.vision_cache (image_url, source_id, model, raw_response, extracted_attrs) "
                    "VALUES (%s, %s, %s, %s, %s::jsonb) "
                    "ON CONFLICT (image_url) DO UPDATE SET source_id=EXCLUDED.source_id, "
                    "model=EXCLUDED.model, raw_response=EXCLUDED.raw_response, "
                    "extracted_attrs=EXCLUDED.extracted_attrs, created_at=now()",
                    (image_url, source_id, model, raw_response, json.dumps(extracted_attrs, ensure_ascii=False)),
                )
        finally:
            await conn.close()
        # 사람이 읽기 쉬운 JSON 파일도 남김
        try:
            self._json_dir.mkdir(parents=True, exist_ok=True)
            name = hashlib.sha1(image_url.encode()).hexdigest()[:16] + ".json"
            (self._json_dir / name).write_text(
                json.dumps(
                    {"image_url": image_url, "source_id": source_id, "model": model,
                     "attributes": extracted_attrs, "raw_response": raw_response},
                    ensure_ascii=False, indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001 — 파일 덤프 실패는 무시(캐시는 DB가 진실원천)
            pass
