"""IngestRunner — 관리 명령이 공유하는 단일 적재 로직 (ADR-0008/0011).

초기 전체 적재(ingest_products)와 폴링 delta(sync_poll)가 같은 apply() 경로를 쓴다.
기본은 LLM 없는 무료 구조 추출(브랜드 + field_info 정형 스펙), --llm이면 텍스트에서
Functional Attribute까지 추출한다.
"""
from __future__ import annotations

import os
from dataclasses import asdict

from apps.extraction.extractor import ExtractionResult, StructuredExtractor
from apps.extraction.field_info import field_info_attributes
from apps.sync.poller import DiffPoller
from apps.sync.watermark import SyncWatermark

WATERMARK_KEY = "kolab:it_update_time"


class StructuredFieldInfoExtractor:
    """LLM 없이 브랜드 + field_info(옵션 레벨) 정형 스펙을 상품 속성으로 병합한다(무료)."""

    def __init__(self):
        self._brand = StructuredExtractor()

    async def extract(self, doc) -> ExtractionResult:
        base = await self._brand.extract(doc)
        attributes = list(base.attributes)
        seen = {a.name for a in attributes}
        for variant in getattr(doc, "variants", None) or []:
            field_info = (getattr(variant, "raw", None) or {}).get("field_info")
            if not field_info:
                continue
            for attr in field_info_attributes(field_info):
                if attr.name not in seen:  # 상품 레벨 병합, 첫 값 우선
                    attributes.append(attr)
                    seen.add(attr.name)
        return ExtractionResult(product_type=base.product_type, attributes=attributes)


def build_extractor(use_llm: bool = False):
    """--llm이면 OpenAI 텍스트 추출, 아니면 무료 구조 추출."""
    if use_llm:
        from apps.agent.openai_client import OpenAILLM
        from apps.extraction.extractor import AttributeExtractor

        return AttributeExtractor(OpenAILLM())
    return StructuredFieldInfoExtractor()


class IngestRunner:
    """C(소스 하이드레이션, ADR-0016): 상품 사실은 우리 DB에 복제하지 않는다.

    적재는 상품마다 assemble → (설명 강화) 임베딩만 저장한다. kg_embedding이 '적재된 상품'
    인덱스이자 content-hash 게이트가 된다(별도 상품/속성 테이블 없음). 속성은 임베딩 텍스트
    구성에만 쓰고 저장하지 않는다 — 채팅 때 소스에서 재추출(ProductEnricher)한다.
    """

    def __init__(self, connector, extractor, embedder, describer=None, pdf_extractor=None):
        self._connector = connector
        self._extractor = extractor
        self._embedder = embedder     # EmbeddingStore: 임베딩 + content-hash 인덱스(필수)
        self._describer = describer    # Route C: 있으면 임베딩 텍스트를 LLM 설명으로 강화
        self._pdf_extractor = pdf_extractor  # 있으면 상품 PDF를 읽어 설명을 강화(INGEST_PDF)

    async def apply(self, source_id: str, *, gate: bool = False) -> str:
        """한 상품을 현재 상태로 반영한다(멱등). 반환: created|updated|unchanged|deleted."""
        doc = await self._connector.assemble(source_id)
        if doc is None:
            await self._embedder.delete(source_id)
            if self._describer is not None:
                await self._describer.delete(source_id)
            return "deleted"
        stored = await self._embedder.get_content_hash(source_id)
        if gate and stored == doc.content_hash:
            return "unchanged"  # content-hash 게이팅: 재추출·재임베딩 생략
        result = await self._extractor.extract(doc)
        values = " ".join(str(a.value) for a in result.attributes)
        description = ""
        if self._describer is not None:  # Route C: LLM 설명으로 강화(게이팅·폴백 내부처리)
            pdf_text = ""
            pdf_url = getattr(doc, "pdf_url", "")
            if (self._pdf_extractor is not None and pdf_url
                    and not await self._describer.is_current(source_id, doc.content_hash)):
                # PDF 문서 강화: 이미 최신 설명이면 fetch 스킵(설명 캐시를 게이트로 재사용)
                pdf_text = await self._pdf_extractor.extract(pdf_url)
            attrs = [asdict(a) for a in result.attributes]
            description = await self._describer.describe(
                source_id, doc.name, attrs, doc.content_hash, pdf_text=pdf_text)
        text = f"{doc.name} {values}".strip()
        if description:
            text = f"{text}\n{description}"
        from apps.embeddings.filters import extract_filters
        await self._embedder.embed_product(
            source_id, doc.name, text, doc.content_hash, filters=extract_filters(doc))
        return "updated" if stored is not None else "created"

    def _batch_size(self, batch_size: int | None) -> int:
        return batch_size or int(os.environ.get("INGEST_BATCH_SIZE", "500"))

    async def _flush(self, ids: list[str], counts: dict[str, int]) -> None:
        for source_id in ids:
            status = await self.apply(source_id)
            counts[status] = counts.get(status, 0) + 1

    async def full_load(self, limit: int | None = None, batch_size: int | None = None) -> dict[str, int]:
        """초기 전체 적재 — 키셋 스트리밍 + 배치(대규모 확장, 이슈 06).

        상품은 1건씩 처리·해제(순차)라 peak 메모리는 1 doc으로 바운드된다.
        """
        size = self._batch_size(batch_size)
        counts: dict[str, int] = {}
        await self._embedder.ensure_indexes()  # kg_embedding 테이블·검색 인덱스 선생성
        if self._describer is not None:
            await self._describer.ensure()
        async with self._connector.session():  # 소스 커넥션 1개 재사용(이슈 04)
            pending: list[str] = []
            async for source_id in self._connector.iter_product_ids(limit=limit):
                pending.append(source_id)
                if len(pending) >= size:
                    await self._flush(pending, counts)
                    pending = []
            if pending:
                await self._flush(pending, counts)
        return counts

    async def _apply_ids(self, ids: list[str], counts: dict[str, int]) -> None:
        """변경 id 집합을 반영한다(소스 커넥션 재사용)."""
        if not ids:
            return
        async with self._connector.session():
            for source_id in ids:
                status = await self.apply(source_id, gate=True)
                counts[status] = counts.get(status, 0) + 1

    async def sync_once(self, poller: DiffPoller | None = None) -> dict[str, int]:
        """전체 재조정 — 소스 스냅샷 대비 삭제·드리프트까지 보정한다(저빈도용).

        안전장치: 우리 DB엔 상품이 있는데 소스 스냅샷이 비면(소스 장애/오설정 정황)
        전량 삭제를 하지 않고 건너뛴다.
        """
        poller = poller or DiffPoller(self._connector)
        previous = await self._embedder.content_hashes()
        changes, current = await poller.poll(previous)
        if previous and not current:
            return {"skipped_empty_source": len(previous)}
        counts: dict[str, int] = {}
        await self._apply_ids([c.source_id for c in changes], counts)
        return counts

    async def sync_incremental(self, watermark_store: SyncWatermark | None = None) -> dict[str, int]:
        """증분 — it_update_time > watermark 인 상품만 반영하고 watermark를 전진한다(저부하).

        it_update_time이 없으면 {"incremental_unavailable": 1}을 반환한다(워커가 재조정으로 폴백).
        """
        watermark_store = watermark_store or SyncWatermark()
        latest = await self._connector.latest_update_time()
        if latest is None:
            return {"incremental_unavailable": 1}
        watermark = await watermark_store.get(WATERMARK_KEY)
        changed = [sid async for sid in self._connector.changed_since(watermark)]
        counts: dict[str, int] = {}
        await self._apply_ids(changed, counts)
        await watermark_store.set(WATERMARK_KEY, latest)
        return counts
