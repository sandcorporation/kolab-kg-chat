"""이슈 01 — ProductDescriber: 상품 한/영 설명 생성 + content-hash 캐시·게이팅."""
from langchain_core.messages import AIMessage

from apps.embeddings.describe import DescriptionStore, ProductDescriber
from tests.fake_chat import ScriptedChatModel


async def _store() -> DescriptionStore:
    s = DescriptionStore(table="kg_description_test")
    await s.reset()
    return s


async def test_describe_generates_and_caches():
    model = ScriptedChatModel(responses=[AIMessage(content="유리 플라스크. Glass flask. 키워드: 플라스크, flask")])
    store = await _store()
    desc = await ProductDescriber(model, store).describe(
        "p1", "Flask", [{"name": "material", "value": "glass"}], content_hash="h1")

    assert "flask" in desc.lower()
    ch, cached = await store.get("p1")
    assert ch == "h1" and cached == desc            # content_hash와 함께 저장


class _CountingModel(ScriptedChatModel):
    calls: int = 0

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        return await super()._agenerate(messages, stop, run_manager, **kwargs)


async def test_unchanged_product_reuses_cache_without_llm():
    model = _CountingModel(responses=[AIMessage(content="설명")])
    store = await _store()
    d = ProductDescriber(model, store)

    await d.describe("p1", "N", [], content_hash="h1")
    desc2 = await d.describe("p1", "N", [], content_hash="h1")   # 같은 hash → 캐시

    assert model.calls == 1                          # LLM 재호출 없음
    assert desc2 == "설명"


class _RecordingModel(ScriptedChatModel):
    last_human: str = ""

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.last_human = messages[-1].content
        return await super()._agenerate(messages, stop, run_manager, **kwargs)


async def test_describe_injects_pdf_text_into_prompt():
    model = _RecordingModel(responses=[AIMessage(content="설명")])
    store = await _store()
    await ProductDescriber(model, store).describe(
        "p1", "Flask", [], content_hash="h1", pdf_text="붕규산 유리 내열 스펙 250mL")
    assert "문서 발췌" in model.last_human
    assert "붕규산 유리 내열 스펙 250mL" in model.last_human


async def test_describe_without_pdf_text_omits_excerpt():
    model = _RecordingModel(responses=[AIMessage(content="설명")])
    store = await _store()
    await ProductDescriber(model, store).describe("p1", "Flask", [], content_hash="h1")
    assert "문서 발췌" not in model.last_human


async def test_is_current_reflects_cache():
    store = await _store()
    d = ProductDescriber(ScriptedChatModel(responses=[AIMessage(content="설명")]), store)
    assert await d.is_current("p1", "h1") is False    # 저장 전
    await d.describe("p1", "N", [], content_hash="h1")
    assert await d.is_current("p1", "h1") is True      # 같은 hash → 최신
    assert await d.is_current("p1", "h2") is False     # 다른 hash → 아님


class _BoomModel(ScriptedChatModel):
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("boom")


async def test_generation_failure_falls_back_to_empty():
    store = await _store()
    desc = await ProductDescriber(_BoomModel(responses=[AIMessage(content="x")]), store).describe(
        "p1", "N", [], content_hash="h1")
    assert desc == ""                                # 예외 전파 안 함
