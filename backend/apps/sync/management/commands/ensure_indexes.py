"""임베딩 저장소 테이블·검색 인덱스를 멱등 생성/점검한다(대규모 적재·조회 필수).

C(소스 하이드레이션): 우리 DB엔 임베딩·설명만 있으므로 kg_embedding(pgvector +
name pg_trgm) · kg_description 인덱스를 보장한다.

    docker compose ... run --rm api python manage.py ensure_indexes
"""
import asyncio

from django.core.management.base import BaseCommand

from apps.embeddings.describe import DescriptionStore
from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider


class Command(BaseCommand):
    help = "임베딩(kg_embedding)·설명(kg_description) 테이블·검색 인덱스를 멱등 생성한다."

    def handle(self, *args, **options):
        async def _run():
            await EmbeddingStore(OpenAIEmbeddingProvider()).ensure_indexes()
            await DescriptionStore().ensure()

        asyncio.run(_run())
        self.stdout.write(self.style.SUCCESS("indexes ensured (kg_embedding, kg_description)"))
