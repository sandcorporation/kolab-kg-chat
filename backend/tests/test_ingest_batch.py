"""ADR-0016 — IngestRunner 배치 full_load: 키셋 스트리밍 + 멱등(C: embedder 인덱스).

C에선 상품 스토어가 없어 GraphStore 배치 세션(커넥션 재사용·배치 커밋)은 제거됐다.
임베딩 저장이 상품당 커넥션을 열지만, 임베딩 API 콜이 지배적이라 영향은 미미하다.
"""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.embeddings.store import EmbeddingStore, FakeEmbeddingProvider
from apps.sync.runner import IngestRunner, StructuredFieldInfoExtractor

ALL_IDS = {"1712107033", "1548728629", "1667982841", "DLM-4"}


async def _runner():
    embedder = EmbeddingStore(FakeEmbeddingProvider(), table="kg_embedding_test")
    await embedder.reset()
    runner = IngestRunner(
        YoungcartMySQLConnector.from_env(), StructuredFieldInfoExtractor(), embedder=embedder
    )
    return embedder, runner


async def test_batched_full_load_ingests_all_and_idempotent():
    embedder, runner = await _runner()
    counts = await runner.full_load(batch_size=2)
    assert counts.get("created") == 4
    assert set(await embedder.content_hashes()) == ALL_IDS

    # 재실행 멱등(중복 없음, 갱신으로 반영)
    runner2 = IngestRunner(
        YoungcartMySQLConnector.from_env(), StructuredFieldInfoExtractor(), embedder=embedder
    )
    counts2 = await runner2.full_load(batch_size=2)
    assert counts2.get("updated") == 4
    assert set(await embedder.content_hashes()) == ALL_IDS
