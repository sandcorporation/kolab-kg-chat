"""영카트(그누보드) MySQL/MariaDB 소스용 SourceConnector 구현 (이슈 04/26).

실제 kolabshop 덤프(MariaDB 10.5, DB `kolabshop2024`)의 스키마에 맞춘다:
- g5_shop_item: it_img1~30, 브랜드=it_brand, 카테고리는 코드(ca_id/2/3)만(이름 테이블 없음)
- g5_shop_item_option: io_catno(카탈로그), io_description(스펙 라벨), io_unit, io_price(절대가)
소스 SQL·매핑·content_hash를 이 모듈 뒤에 은닉하고, source-agnostic ProductDocument를 낸다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Awaitable, Callable

import aiomysql

from apps.connectors.base import (
    ProductChanged,
    ProductDocument,
    SourceImage,
    SourceVariant,
)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_IMG_SRC_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)
_MAX_IMG = 30  # 실제 스키마: it_img1~30


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()


def extract_img_srcs(html: str | None) -> list[str]:
    """it_explan HTML에 박힌 스펙 이미지 <img src>를 순서대로 추출한다(이슈 01)."""
    if not html:
        return []
    return _IMG_SRC_RE.findall(html)


_IMAGE_BASE = "https://www.kolabshop.com/data/item/"


def normalize_image_url(url: str | None) -> str | None:
    """상대경로는 kolabshop 절대 URL로, 'no-image' 플레이스홀더는 제외(비전 대상 정제)."""
    if not url:
        return None
    low = url.lower()
    if "no-image" in low or "no_image" in low or "noimage" in low:
        return None
    if url.startswith("http"):
        return url
    return _IMAGE_BASE + url.lstrip("/")


def _content_hash(
    name, brand, category_path, description_text, images, variants
) -> str:
    payload = {
        "name": name,
        "brand": brand,
        "category_path": category_path,
        "description_text": description_text,
        "images": [[i.url, i.position] for i in images],
        "variants": [[v.variant_key, v.label, v.price] for v in variants],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


class YoungcartMySQLConnector:
    def __init__(self, connect: Callable[[], Awaitable[aiomysql.Connection]]):
        self._connect = connect
        self._session_conn = None  # session() 내 재사용 커넥션
        self._page_size = int(os.environ.get("INGEST_PAGE_SIZE", "1000"))

    # ── 커넥션 수명 (session이면 재사용) ──
    async def _acquire(self):
        if self._session_conn is not None:
            return self._session_conn
        return await self._connect()

    def _release(self, conn) -> None:
        if conn is not self._session_conn:
            conn.close()  # aiomysql close는 동기

    @asynccontextmanager
    async def session(self):
        """배치 동안 소스 커넥션 1개를 재사용한다(상품마다 새로 열지 않도록)."""
        conn = await self._connect()
        self._session_conn = conn
        try:
            yield self
        finally:
            self._session_conn = None
            conn.close()

    @classmethod
    def from_env(cls) -> "YoungcartMySQLConnector":
        async def connect() -> aiomysql.Connection:
            return await aiomysql.connect(
                host=os.environ["SOURCE_DB_HOST"],
                port=int(os.environ.get("SOURCE_DB_PORT", "3306")),
                user=os.environ["SOURCE_DB_USER"],
                password=os.environ["SOURCE_DB_PASSWORD"],
                db=os.environ["SOURCE_DB_NAME"],
                charset="utf8mb4",
            )

        return cls(connect)

    async def iter_product_ids(self, limit: int | None = None, page_size: int | None = None):
        """it_id 키셋 페이지네이션으로 스트리밍한다 — 전체 id를 한 번에 버퍼링하지 않는다(이슈 04)."""
        page = page_size or self._page_size
        remaining = limit
        last = ""
        conn = await self._acquire()
        try:
            while True:
                size = min(page, remaining) if remaining is not None else page
                if size <= 0:
                    break
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT it_id FROM g5_shop_item WHERE it_use = 1 AND it_id > %s "
                        "ORDER BY it_id LIMIT %s",
                        (last, size),
                    )
                    rows = await cur.fetchall()
                if not rows:
                    break
                for (it_id,) in rows:
                    yield it_id
                last = rows[-1][0]
                if remaining is not None:
                    remaining -= len(rows)
                if len(rows) < size:
                    break
        finally:
            self._release(conn)

    async def latest_update_time(self) -> str | None:
        """소스의 최대 it_update_time(증분 watermark용). 컬럼 부재 시 None(재조정 폴백 신호)."""
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        "SELECT MAX(it_update_time) FROM g5_shop_item WHERE it_use = 1"
                    )
                    (val,) = await cur.fetchone()
                except Exception:  # noqa: BLE001 — it_update_time 컬럼 부재
                    return None
        finally:
            self._release(conn)
        return str(val) if val is not None else None

    async def changed_since(self, watermark: str | None):
        """it_update_time > watermark 인 변경 Product id를 산출한다(이슈 05)."""
        wm = watermark or "1970-01-01 00:00:00"
        conn = await self._acquire()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT it_id FROM g5_shop_item WHERE it_use = 1 AND it_update_time > %s "
                    "ORDER BY it_update_time, it_id",
                    (wm,),
                )
                rows = await cur.fetchall()
        finally:
            self._release(conn)
        for (it_id,) in rows:
            yield it_id

    async def assemble(self, source_id: str) -> ProductDocument | None:
        conn = await self._acquire()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM g5_shop_item WHERE it_id = %s", (source_id,))
                item = await cur.fetchone()
                if item is None:
                    return None
                await cur.execute(
                    "SELECT io_no, io_catno, io_model, io_description, io_unit, io_price "
                    "FROM g5_shop_item_option WHERE it_id = %s AND io_use = 1 ORDER BY io_no",
                    (source_id,),
                )
                option_rows = await cur.fetchall()
                # field_info(구조 스펙)를 material_number(=io_catno)로 조인 — 테이블 없으면 스킵
                try:
                    await cur.execute(
                        "SELECT * FROM g5_shop_item_field_info WHERE it_id = %s", (source_id,)
                    )
                    field_rows = await cur.fetchall()
                except Exception:  # noqa: BLE001 — mock 등 테이블 부재 시
                    field_rows = []
                field_by_catno = {(fr.get("material_number") or ""): dict(fr) for fr in field_rows}
        finally:
            self._release(conn)

        base_price = item.get("it_price") or 0
        variants = []
        for o in option_rows:
            raw = {**o, "catalog_number": o.get("io_catno")}
            field_info = field_by_catno.get(o.get("io_catno") or "")
            if field_info:
                raw["field_info"] = field_info
            variants.append(
                SourceVariant(
                    variant_key=str(o["io_no"]),
                    label=(o.get("io_description") or o.get("io_catno") or o.get("io_model") or "").strip(),
                    # 이 쇼핑몰의 io_price는 절대가(관측). 옵션가 없으면 상품 기본가로 폴백.
                    price=(o.get("io_price") or base_price) or None,
                    raw=raw,
                )
            )

        # 갤러리 + explan 이미지: URL 정규화(절대화·플레이스홀더 스킵) + 중복 제거
        images: list[SourceImage] = []
        seen_urls: set[str] = set()
        for i in range(1, _MAX_IMG + 1):
            url = normalize_image_url(item.get(f"it_img{i}"))
            if url and url not in seen_urls:
                seen_urls.add(url)
                images.append(SourceImage(url=url, position=len(images) + 1, source="gallery"))
        for raw_url in extract_img_srcs(item.get("it_explan")):
            url = normalize_image_url(raw_url)
            if url and url not in seen_urls:
                seen_urls.add(url)
                images.append(SourceImage(url=url, position=len(images) + 1, source="explan"))
        description_text = _strip_html(
            " ".join(filter(None, [item.get("it_basic"), item.get("it_explan")]))
        )
        brand = (item.get("it_brand") or item.get("it_maker") or "").strip() or None
        # 카테고리 이름 테이블이 덤프에 없으므로 코드만 보존(ca_id/ca_id2/ca_id3).
        category_path = [
            c.strip()
            for c in (item.get("ca_id"), item.get("ca_id2"), item.get("ca_id3"))
            if c and c.strip()
        ]

        return ProductDocument(
            source_id=item["it_id"],
            name=item["it_name"],
            brand=brand,
            category_path=category_path,
            description_text=description_text,
            images=images,
            variants=variants,
            content_hash=_content_hash(
                item["it_name"], brand, category_path, description_text, images, variants
            ),
            raw=dict(item),
            fetched_at=datetime.now(timezone.utc),
        )

    async def subscribe_changes(self):
        # 이슈 14(폴러)·26(실제 CDC)에서 구현. 현재는 빈 스트림.
        if False:  # pragma: no cover
            yield ProductChanged("", "")
