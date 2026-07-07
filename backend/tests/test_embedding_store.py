"""이슈 01 — EmbeddingStore(운영): 최근접 검색 + 임베딩 캐시 + 모델 버전 태깅."""
from apps.embeddings.store import EmbeddingStore, FakeEmbeddingProvider


async def test_search_returns_nearest_by_similarity():
    store = EmbeddingStore(FakeEmbeddingProvider(dim=8), table="kg_embedding_test")
    await store.reset()
    await store.embed_product("p1", "메스플라스크", "유리 플라스크 메스실린더")
    await store.embed_product("p2", "피펫", "전동 피펫 에이드")
    await store.embed_product("p3", "시약", "중수소수 시약")

    hits = await store.search("유리 플라스크 메스실린더", k=1)  # p1 텍스트와 동일
    assert hits[0]["source_id"] == "p1"


async def test_embed_product_is_cached():
    class CountingProvider(FakeEmbeddingProvider):
        def __init__(self):
            super().__init__(dim=8)
            self.calls = 0

        async def embed(self, texts):
            self.calls += 1
            return await super().embed(texts)

    provider = CountingProvider()
    store = EmbeddingStore(provider, table="kg_embedding_test")
    await store.reset()

    assert await store.embed_product("p1", "N", "같은 텍스트") is True
    assert await store.embed_product("p1", "N", "같은 텍스트") is False  # 동일 텍스트 → 스킵
    assert provider.calls == 1


async def test_model_version_isolates_search():
    v1 = EmbeddingStore(FakeEmbeddingProvider("m1", dim=8), table="kg_embedding_test")
    await v1.reset()
    await v1.embed_product("p1", "N", "텍스트")
    v2 = EmbeddingStore(FakeEmbeddingProvider("m2", dim=8), table="kg_embedding_test")
    # m2 모델로는 임베딩이 없다 → 검색 결과 없음(모델끼리만 비교)
    assert await v2.search("텍스트", k=5) == []


async def test_ann_index_preserves_nearest_search():
    # HNSW 근사인덱스를 빌드해도 최근접 검색은 그대로 정확해야 한다(재현율 보존).
    store = EmbeddingStore(FakeEmbeddingProvider(dim=8), table="kg_embedding_test")
    await store.reset()
    await store.embed_product("p1", "메스플라스크", "유리 플라스크 메스실린더")
    await store.embed_product("p2", "피펫", "전동 피펫 에이드")
    await store.embed_product("p3", "시약", "중수소수 시약")

    assert await store.ensure_ann_index() is True          # 데이터 있음 → 빌드
    hits = await store.search("유리 플라스크 메스실린더", k=1)   # 인덱스 후에도 정확
    assert hits[0]["source_id"] == "p1"


async def test_ann_index_noop_when_empty():
    # 데이터가 없으면 차원을 유도할 수 없어 안전하게 건너뛴다(False).
    store = EmbeddingStore(FakeEmbeddingProvider(dim=8), table="kg_embedding_test")
    await store.reset()
    assert await store.ensure_ann_index() is False


async def test_ann_index_is_idempotent():
    # 두 번 호출해도 오류 없이 인덱스가 보장되고 검색은 정확하다.
    store = EmbeddingStore(FakeEmbeddingProvider(dim=8), table="kg_embedding_test")
    await store.reset()
    await store.embed_product("p1", "N", "텍스트")
    assert await store.ensure_ann_index() is True
    assert await store.ensure_ann_index() is True          # 재호출도 안전(이미 존재)
    assert (await store.search("텍스트", k=1))[0]["source_id"] == "p1"
