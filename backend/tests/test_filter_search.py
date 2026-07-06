"""이슈 02 (ADR-0018) — 필터 검색: 겹침 WHERE, NULL 제외, 다중 AND."""
from apps.embeddings.store import EmbeddingStore, FakeEmbeddingProvider


async def _store():
    emb = EmbeddingStore(FakeEmbeddingProvider(), table="kg_embedding_test")
    await emb.reset()
    await emb.embed_product("cheap", "cheap item", "cheap", "h", filters={"price": (10000.0, 10000.0)})
    await emb.embed_product("mid", "mid item", "mid", "h", filters={"price": (5000000.0, 5000000.0)})
    await emb.embed_product("pricey", "pricey item", "exp", "h", filters={"price": (50000000.0, 50000000.0)})
    await emb.embed_product("noprice", "noprice item", "np", "h", filters={})
    return emb


async def test_price_max_filter_excludes_over_and_null():
    emb = await _store()
    hits = await emb.search("item", k=10, filters={"price": (None, 30000000.0)})  # ≤3천만
    assert {h["source_id"] for h in hits} == {"cheap", "mid"}  # pricey·noprice(NULL) 제외


async def test_keyword_search_applies_filter():
    emb = await _store()
    hits = await emb.keyword_search("item", limit=10, filters={"price": (None, 30000000.0)})
    assert {h["source_id"] for h in hits} == {"cheap", "mid"}


async def test_no_filter_returns_all():
    emb = await _store()
    assert len(await emb.search("item", k=10)) == 4


async def test_range_filter_overlap():
    emb = EmbeddingStore(FakeEmbeddingProvider(), table="kg_embedding_test")
    await emb.reset()
    await emb.embed_product("fridge", "a", "a", "h", filters={"storage_temp": (2.0, 8.0)})
    await emb.embed_product("frozen", "b", "b", "h", filters={"storage_temp": (-20.0, -20.0)})
    hits = await emb.search("a", k=10, filters={"storage_temp": (2.0, 8.0)})  # 냉장 2~8 겹침
    assert {h["source_id"] for h in hits} == {"fridge"}  # frozen 제외


async def test_multiple_filters_and():
    emb = EmbeddingStore(FakeEmbeddingProvider(), table="kg_embedding_test")
    await emb.reset()
    await emb.embed_product("good", "a", "a", "h",
                            filters={"price": (1000.0, 1000.0), "purity": (99.9, 99.9)})
    await emb.embed_product("cheap_lowpure", "b", "b", "h",
                            filters={"price": (1000.0, 1000.0), "purity": (90.0, 90.0)})
    hits = await emb.search("a", k=10, filters={"price": (None, 5000.0), "purity": (99.0, None)})
    assert {h["source_id"] for h in hits} == {"good"}  # 가격·순도 둘 다 만족만
