"""이슈 03 — 적재 시 임베딩 + content-hash 게이팅(ADR-0012)."""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.embeddings.store import EmbeddingStore, FakeEmbeddingProvider
from apps.graph.store import GraphStore
from apps.sync.runner import IngestRunner, StructuredFieldInfoExtractor


class CountingProvider(FakeEmbeddingProvider):
    def __init__(self):
        super().__init__(dim=8)
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        return await super().embed(texts)


async def _runner(provider):
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    embedder = EmbeddingStore(provider, table="kg_embedding_test")
    await embedder.reset()
    runner = IngestRunner(
        store, YoungcartMySQLConnector.from_env(), StructuredFieldInfoExtractor(), embedder=embedder
    )
    return store, embedder, runner


async def test_apply_embeds_new_product():
    _, embedder, runner = await _runner(CountingProvider())
    assert await runner.apply("1548728629") == "created"
    hits = await embedder.search("Volumetric Flask", k=1)
    assert hits and hits[0]["source_id"] == "1548728629"


async def test_gated_unchanged_skips_embedding():
    provider = CountingProvider()
    _, _, runner = await _runner(provider)
    await runner.apply("1548728629")            # created → 임베딩(1회)
    assert provider.calls == 1
    assert await runner.apply("1548728629", gate=True) == "unchanged"  # 게이팅
    assert provider.calls == 1                  # 재임베딩 없음
