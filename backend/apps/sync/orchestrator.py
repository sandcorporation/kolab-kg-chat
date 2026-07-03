"""SyncOrchestrator — 쓰기 경로 워커 (이슈 13/14, ADR-0008).

한 Product의 전체 반영 경로를 묶는다: assemble → upsert → 속성 추출(텍스트+이미지)
→ 속성/변형 속성 저장. 초기 전체 적재와 delta가 같은 경로를 쓰며,
delta는 content-hash 게이팅으로 안 바뀐 Product의 비싼 추출을 생략한다.
임베딩·시맨틱 검색은 제거되었다(ADR-0010).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class IngestDeps:
    connector: Any
    store: Any
    extractor: Any
    variant_classifier: Any
    image_extractor: Any


async def _process_doc(deps: IngestDeps, doc) -> None:
    """이미 조립된 ProductDocument를 그래프에 완전 반영한다."""
    await deps.store.upsert_product(doc)

    result = await deps.extractor.extract(doc)
    known = frozenset(a.name for a in result.attributes)
    # 비전 실패(이미지 fetch/파싱 오류)는 해당 상품 이미지 속성만 생략하고 수집을 지속(이슈 04)
    try:
        image_result = await deps.image_extractor.extract(
            result.product_type, doc.images, known_names=known
        )
        image_attributes = image_result.attributes
    except Exception:  # noqa: BLE001
        image_attributes = []
    await deps.store.set_attributes(
        doc.source_id, [asdict(a) for a in (result.attributes + image_attributes)]
    )

    classified = await deps.variant_classifier.classify(result.product_type, doc.variants)
    for cv in classified:
        if cv.kind == "functional":
            await deps.store.set_variant_attributes(
                cv.variant_key, [asdict(a) for a in cv.attributes]
            )


async def process_product(deps: IngestDeps, source_id: str) -> bool:
    doc = await deps.connector.assemble(source_id)
    if doc is None:
        await deps.store.delete_product(source_id)
        return False
    await _process_doc(deps, doc)
    return True


async def run_full_load(deps: IngestDeps) -> int:
    """초기 전체 적재 — 소스의 모든 Product를 처리하고 건수를 반환한다."""
    count = 0
    async for source_id in deps.connector.iter_product_ids():
        if await process_product(deps, source_id):
            count += 1
    return count


async def process_delta(deps: IngestDeps, source_id: str) -> str:
    """변경 신호로 한 Product를 현재 상태로 반영한다(content-hash 게이팅).

    반환: "created" | "updated" | "unchanged" | "deleted"
    """
    doc = await deps.connector.assemble(source_id)
    if doc is None:
        await deps.store.delete_product(source_id)
        return "deleted"

    stored_hash = await deps.store.get_content_hash(source_id)
    if stored_hash == doc.content_hash:
        return "unchanged"  # 게이팅: 비싼 추출/비전 생략

    await _process_doc(deps, doc)
    return "created" if stored_hash is None else "updated"


def coalesce(changes) -> dict[str, str]:
    """버스트 변경을 Product 단위로 합친다(마지막 op 유지) → 재처리 1회."""
    out: dict[str, str] = {}
    for change in changes:
        out[change.source_id] = change.op
    return out


async def process_changes(deps: IngestDeps, changes) -> dict[str, str]:
    """코얼레싱 후 각 Product를 1회 delta 처리한다. {source_id: status} 반환."""
    return {sid: await process_delta(deps, sid) for sid in coalesce(changes)}
