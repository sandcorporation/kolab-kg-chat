"""소스 DB의 상품을 지식그래프로 적재한다(멱등). ingest_real.py를 대체.

    docker compose ... run --rm api python manage.py ingest_products [--limit N] [--llm]
"""
import asyncio
import os

from django.core.management.base import BaseCommand

from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore
from apps.sync.runner import IngestRunner, build_extractor


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


class Command(BaseCommand):
    help = "소스 DB의 상품을 지식그래프(knowledge_graph)로 적재한다(멱등)."

    def add_arguments(self, parser):
        # 배치/페이지 크기는 env(INGEST_BATCH_SIZE·INGEST_PAGE_SIZE)로도 제어된다. CLI가 우선.
        parser.add_argument(
            "--limit", type=int, default=None, help="적재할 최대 상품 수(기본: 전체)"
        )
        parser.add_argument(
            "--batch-size", type=int, default=None,
            help="배치 크기(커밋 주기). 기본 env INGEST_BATCH_SIZE 또는 500.",
        )
        parser.add_argument(
            "--llm", action="store_true", default=_env_bool("INGEST_LLM"),
            help="LLM으로 Functional Attribute까지 추출(비용 발생). env INGEST_LLM. 기본은 무료 구조 추출.",
        )

    def handle(self, *args, **options):
        counts = asyncio.run(self._run(options["limit"], options["batch_size"], options["llm"]))
        self.stdout.write(self.style.SUCCESS(f"ingested into knowledge_graph: {counts}"))

    async def _run(self, limit, batch_size, use_llm):
        from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider

        runner = IngestRunner(
            GraphStore(), YoungcartMySQLConnector.from_env(), build_extractor(use_llm),
            embedder=EmbeddingStore(OpenAIEmbeddingProvider()),  # ADR-0012: 적재 시 임베딩
        )
        return await runner.full_load(limit=limit, batch_size=batch_size)
