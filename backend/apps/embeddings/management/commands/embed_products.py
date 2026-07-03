"""knowledge_graph 상품을 임베딩한다(semantic_search 백필, 이슈 01, ADR-0012, 캐시).

이미 적재된 그래프에 임베딩을 채운다. 재실행은 캐시로 안전.

    docker compose run --rm api python manage.py embed_products
"""
import asyncio

from django.core.management.base import BaseCommand

from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider
from apps.graph.store import GraphStore


class Command(BaseCommand):
    help = "knowledge_graph 상품(name+속성값)을 임베딩한다(text-embedding-3-small, 캐시)."

    def add_arguments(self, parser):
        parser.add_argument("--graph", default="knowledge_graph")

    def handle(self, *args, **options):
        new, total = asyncio.run(self._run(options["graph"]))
        self.stdout.write(self.style.SUCCESS(f"embedded {new} new / {total} products"))

    async def _run(self, graph_name):
        store = GraphStore(graph_name=graph_name)
        emb = EmbeddingStore(OpenAIEmbeddingProvider())
        products = await store.list_products()
        new = 0
        for p in products:
            sid, name = p["source_id"], p["name"]
            attrs = await store.get_attributes(sid)
            text = (name + " " + " ".join(str(a["value"]) for a in attrs)).strip()
            if await emb.embed_product(sid, name, text):
                new += 1
        return new, len(products)
