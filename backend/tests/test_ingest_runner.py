"""IngestRunner (ADR-0016, C) — 전체 적재 + 폴링 delta(content-hash 게이팅).

C: 상품 스토어 없이 kg_embedding이 '적재된 상품' 인덱스. 적재 결과는 embedder로 검증한다.
"""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.embeddings.store import EmbeddingStore, FakeEmbeddingProvider
from apps.sync.runner import IngestRunner, StructuredFieldInfoExtractor

ALL_IDS = {"1712107033", "1548728629", "1667982841", "DLM-4", "SOLD-1"}  # 품절 상품도 적재 대상


async def _runner():
    embedder = EmbeddingStore(FakeEmbeddingProvider(), table="kg_embedding_test")
    await embedder.reset()
    runner = IngestRunner(
        YoungcartMySQLConnector.from_env(), StructuredFieldInfoExtractor(), embedder=embedder
    )
    return embedder, runner


async def _ingested(embedder) -> set[str]:
    return set(await embedder.content_hashes())


async def test_full_load_ingests_all_products():
    embedder, runner = await _runner()
    counts = await runner.full_load()

    assert counts.get("created") == 5
    assert await _ingested(embedder) == ALL_IDS


async def test_full_load_respects_limit():
    _, runner = await _runner()
    counts = await runner.full_load(limit=2)
    assert counts.get("created") == 2


async def test_apply_gate_skips_unchanged():
    _, runner = await _runner()
    first = await runner.apply("1548728629")
    assert first == "created"
    again = await runner.apply("1548728629", gate=True)
    assert again == "unchanged"  # 소스 그대로 → content-hash 게이팅


async def test_sync_once_creates_from_empty_index():
    embedder, runner = await _runner()
    counts = await runner.sync_once()  # 빈 인덱스 기준선 → 전부 created
    assert counts.get("created") == 5
    assert await _ingested(embedder) == ALL_IDS


async def test_sync_once_stable_after_full_load():
    _, runner = await _runner()
    await runner.full_load()
    counts = await runner.sync_once()  # 인덱스 == 소스 → 변경 없음
    assert counts == {}


async def test_sync_once_detects_deletion():
    embedder, runner = await _runner()
    await runner.full_load()
    # 인덱스엔 있으나 소스엔 없는 상품 → deleted 로 감지·반영
    await embedder.embed_product("ghost-not-in-source", "Ghost", "ghost text", "ghost-hash")
    counts = await runner.sync_once()
    assert counts.get("deleted") == 1
    assert "ghost-not-in-source" not in await _ingested(embedder)


async def test_sync_once_guards_against_empty_source():
    # 소스가 비면(장애/오설정) 인덱스의 상품을 전량 삭제하지 않고 건너뛴다.
    embedder, runner = await _runner()
    await runner.full_load()

    class EmptyConnector:
        async def iter_product_ids(self, limit=None):
            return
            yield  # pragma: no cover — 빈 async 제너레이터

        async def assemble(self, source_id):
            return None

    empty_runner = IngestRunner(EmptyConnector(), StructuredFieldInfoExtractor(), embedder=embedder)
    counts = await empty_runner.sync_once()

    assert "skipped_empty_source" in counts
    assert await _ingested(embedder) == ALL_IDS  # 삭제 안 됨
