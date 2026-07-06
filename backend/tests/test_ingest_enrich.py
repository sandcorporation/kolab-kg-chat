"""ADR-0016/0015 — IngestRunner 강화 적재(C): 설명이 임베딩 텍스트에 포함된다."""
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.sync.runner import IngestRunner, StructuredFieldInfoExtractor


class RecordingEmbedder:
    """embed_product에 넘어온 텍스트를 기록한다(embedder = 적재 인덱스)."""
    def __init__(self):
        self.texts: dict[str, str] = {}

    async def embed_product(self, source_id, name, text, content_hash=None):
        self.texts[source_id] = text
        return True

    async def get_content_hash(self, source_id):
        return None

    async def delete(self, source_id):
        self.texts.pop(source_id, None)


class FakeDescriber:
    async def describe(self, source_id, name, attributes, content_hash):
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
