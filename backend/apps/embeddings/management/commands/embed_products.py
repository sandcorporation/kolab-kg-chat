"""knowledge_graph 상품을 강화 임베딩한다(Route C 백필, ADR-0012/0014, 캐시).

각 상품에 LLM 설명(한/영)을 붙여 임베딩 텍스트를 강화한다. content-hash로 게이팅되어
재실행·미변경분은 재호출하지 않는다(캐시 안전). 대규모(수십만)는 Batch API 백필이 후속.

    docker compose run --rm api python manage.py embed_products [--concurrency 8]
"""
import asyncio

from django.core.management.base import BaseCommand

from apps.embeddings.describe import build_describer
from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider
from apps.graph.store import GraphStore


class Command(BaseCommand):
    help = "knowledge_graph 상품을 LLM 설명으로 강화 임베딩한다(Route C, 캐시)."

    def add_arguments(self, parser):
        parser.add_argument("--graph", default="knowledge_graph")
        parser.add_argument("--concurrency", type=int, default=8)

    def handle(self, *args, **options):
        new, total = asyncio.run(self._run(options["graph"], options["concurrency"]))
        self.stdout.write(self.style.SUCCESS(f"enriched-embedded {new} new / {total} products"))

    async def _run(self, graph_name, concurrency):
        store = GraphStore(graph_name=graph_name)
        emb = EmbeddingStore(OpenAIEmbeddingProvider())
        describer = build_describer()
        await emb.ensure()        # 동시 백필 전 테이블 선생성(CREATE TABLE 레이스 방지)
        await describer.ensure()
        products = await store.list_products()
        sem = asyncio.Semaphore(concurrency)

        async def one(p) -> bool:
            async with sem:
                sid, name = p["source_id"], p["name"]
                attrs = await store.get_attributes(sid)
                content_hash = await store.get_content_hash(sid) or sid
                desc = await describer.describe(sid, name, attrs, content_hash)
                values = " ".join(str(a["value"]) for a in attrs)
                text = f"{name} {values}".strip()
                if desc:
                    text = f"{text}\n{desc}"
                return await emb.embed_product(sid, name, text)

        results = []
        step = concurrency * 4
        for i in range(0, len(products), step):
            results += await asyncio.gather(*[one(p) for p in products[i:i + step]])
        return sum(results), len(products)
