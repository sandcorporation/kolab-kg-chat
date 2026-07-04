"""eval_graph 코퍼스 상품을 임베딩한다(config 4 semantic_search용, 이슈 04, 캐시).

    docker compose run --rm api python manage.py embed_corpus
"""
import asyncio

from django.core.management.base import BaseCommand

from apps.eval.embeddings import EvalEmbeddings, OpenAIEmbeddingProvider
from apps.graph.store import GraphStore


class Command(BaseCommand):
    help = "eval_graph 코퍼스 상품(name+속성값)을 임베딩한다(text-embedding-3-small, 캐시)."

    def handle(self, *args, **options):
        n, total = asyncio.run(self._run())
        self.stdout.write(self.style.SUCCESS(f"embedded {n} new / {total} corpus products"))

    async def _run(self):
        store = GraphStore(graph_name="eval_graph")
        emb = EvalEmbeddings(OpenAIEmbeddingProvider())
        products = await store.list_products()
        new = 0
        for p in products:
            sid, name = p["source_id"], p["name"]
            attrs = await store.get_attributes(sid)
            text = name + " " + " ".join(str(a["value"]) for a in attrs)
            if await emb.embed_product(sid, name, text.strip()):
                new += 1
        return new, len(products)
