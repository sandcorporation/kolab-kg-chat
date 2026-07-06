"""소스 DB의 상품을 강화 임베딩으로 적재한다(멱등, C: 소스 하이드레이션).

    docker compose ... run --rm api python manage.py ingest_products [--limit N] [--llm]
"""
import asyncio
import os

from django.core.management.base import BaseCommand

from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.sync.runner import IngestRunner, build_extractor


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


class Command(BaseCommand):
    help = "소스 DB의 상품을 강화 임베딩으로 적재한다(멱등, C: 소스 하이드레이션)."

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
        self.stdout.write(self.style.SUCCESS(f"ingested (enriched embeddings): {counts}"))

    async def _run(self, limit, batch_size, use_llm):
        from apps.embeddings.describe import build_describer
        from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider

        runner = IngestRunner(
            YoungcartMySQLConnector.from_env(), build_extractor(use_llm),
            embedder=EmbeddingStore(OpenAIEmbeddingProvider()),  # 임베딩 + content-hash 인덱스
            describer=build_describer(),  # Route C: LLM 설명으로 임베딩 강화
        )
        return await runner.full_load(limit=limit, batch_size=batch_size)
