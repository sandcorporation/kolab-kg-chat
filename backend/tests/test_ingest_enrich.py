"""ADR-0016/0015 — IngestRunner 강화 적재(C): 설명이 임베딩 텍스트에 포함된다."""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.sync.runner import IngestRunner, StructuredFieldInfoExtractor


class RecordingEmbedder:
    """embed_product에 넘어온 텍스트를 기록한다(embedder = 적재 인덱스)."""
    def __init__(self):
        self.texts: dict[str, str] = {}

    async def embed_product(self, source_id, name, text, content_hash=None, filters=None):
        self.texts[source_id] = text
        return True

    async def get_content_hash(self, source_id):
        return None

    async def delete(self, source_id):
        self.texts.pop(source_id, None)


class FakeDescriber:
    async def describe(self, source_id, name, attributes, content_hash, pdf_text=""):
        return "이 상품은 부피 측정용 유리 플라스크입니다. volumetric flask. 키워드: 플라스크, flask"


def _runner(embedder, describer=None):
    return IngestRunner(
        YoungcartMySQLConnector.from_env(), StructuredFieldInfoExtractor(),
        embedder=embedder, describer=describer,
    )


async def test_apply_embeds_enriched_text_with_description():
    embedder = RecordingEmbedder()
    runner = _runner(embedder, describer=FakeDescriber())
    await runner.apply("1548728629")

    text = embedder.texts["1548728629"]
    assert "volumetric flask" in text.lower()        # LLM 설명이 임베딩 텍스트에 포함
    assert "flask" in text.lower()


async def test_apply_without_describer_stays_thin():
    # describer 없으면 현행(상품명+값)만 — 강화 문구 없음
    embedder = RecordingEmbedder()
    runner = _runner(embedder, describer=None)
    await runner.apply("1548728629")
    assert "volumetric flask입니다" not in embedder.texts["1548728629"].lower()


# ── PDF 문서 강화(이슈 02) ──

class _RecordingDescriber:
    def __init__(self, current=False):
        self._current = current
        self.pdf_texts: list[str] = []

    async def is_current(self, source_id, content_hash):
        return self._current

    async def describe(self, source_id, name, attributes, content_hash, pdf_text=""):
        self.pdf_texts.append(pdf_text)
        return "설명"

    async def delete(self, source_id):
        pass


class _CountingPdfExtractor:
    def __init__(self, text):
        self._text = text
        self.calls = 0

    async def extract(self, url):
        self.calls += 1
        return self._text


def _doc_with_pdf(pdf_url):
    from datetime import datetime, timezone

    from apps.connectors.base import ProductDocument

    return ProductDocument(
        source_id="p-pdf", name="Flask", brand="B", category_path=[], description_text="",
        images=[], variants=[], content_hash="h", raw={},
        fetched_at=datetime.now(timezone.utc), pdf_url=pdf_url,
    )


class _OneDocConnector:
    def __init__(self, doc):
        self._doc = doc

    async def assemble(self, source_id):
        return self._doc if source_id == self._doc.source_id else None


async def test_pdf_text_flows_into_describe():
    doc = _doc_with_pdf("http://x/spec.pdf")
    describer = _RecordingDescriber(current=False)
    pdf = _CountingPdfExtractor("붕규산 유리 내열 스펙")
    runner = IngestRunner(
        _OneDocConnector(doc), StructuredFieldInfoExtractor(),
        embedder=RecordingEmbedder(), describer=describer, pdf_extractor=pdf,
    )
    await runner.apply("p-pdf")
    assert pdf.calls == 1                              # PDF fetch 수행
    assert describer.pdf_texts == ["붕규산 유리 내열 스펙"]  # describe로 전달


async def test_pdf_fetch_skipped_when_description_current():
    doc = _doc_with_pdf("http://x/spec.pdf")
    describer = _RecordingDescriber(current=True)      # 이미 최신
    pdf = _CountingPdfExtractor("스펙")
    runner = IngestRunner(
        _OneDocConnector(doc), StructuredFieldInfoExtractor(),
        embedder=RecordingEmbedder(), describer=describer, pdf_extractor=pdf,
    )
    await runner.apply("p-pdf")
    assert pdf.calls == 0                              # fetch 스킵(설명 캐시 게이트)
    assert describer.pdf_texts == [""]                 # describe엔 빈 텍스트


async def test_no_pdf_extractor_leaves_describe_unenriched():
    doc = _doc_with_pdf("http://x/spec.pdf")
    describer = _RecordingDescriber(current=False)
    runner = IngestRunner(
        _OneDocConnector(doc), StructuredFieldInfoExtractor(),
        embedder=RecordingEmbedder(), describer=describer, pdf_extractor=None,
    )
    await runner.apply("p-pdf")
    assert describer.pdf_texts == [""]                 # 미주입이면 PDF 무관
