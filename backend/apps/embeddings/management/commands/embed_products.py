"""소스 상품을 강화 임베딩한다(C 백필, 동시성, 캐시).

각 상품에 LLM 설명(한/영)을 붙여 임베딩 텍스트를 강화한다. content-hash 게이팅으로
재실행·미변경분은 재호출하지 않는다(캐시 안전). ingest_products의 동시성 버전 —
대규모 초기 강화용(LLM 설명·임베딩 호출을 병렬화). 수십만 규모는 Batch API가 후속.

    docker compose run --rm api python manage.py embed_products [--concurrency 8] [--limit N]
"""
import asyncio
from dataclasses import asdict

from django.core.management.base import BaseCommand

from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.embeddings.describe import build_describer
from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider
from apps.sync.runner import build_extractor


class Command(BaseCommand):
    help = "소스 상품을 LLM 설명으로 강화 임베딩한다(C 백필, 동시성, 캐시)."

    def add_arguments(self, parser):
        parser.add_argument("--concurrency", type=int, default=8)
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **options):
        new, total = asyncio.run(self._run(options["concurrency"], options["limit"]))
        self.stdout.write(self.style.SUCCESS(f"enriched-embedded {new} new / {total} products"))

    async def _run(self, concurrency, limit):
        connector = YoungcartMySQLConnector.from_env()
        extractor = build_extractor(use_llm=False)
        emb = EmbeddingStore(OpenAIEmbeddingProvider())
        describer = build_describer()
        await emb.ensure()        # 동시 백필 전 테이블·인덱스 선생성(CREATE TABLE 레이스 방지)
        await describer.ensure()

        # id 수집만 세션(단일 커넥션)에서 순차로, 처리는 각자 커넥션으로(동시성 안전).
        async with connector.session():
            ids = [sid async for sid in connector.iter_product_ids(limit=limit)]

        sem = asyncio.Semaphore(concurrency)

        async def one(sid: str) -> bool:
            async with sem:
                doc = await connector.assemble(sid)  # 세션 밖 → 자체 커넥션(동시 안전)
                if doc is None:
                    return False
                result = await extractor.extract(doc)
                values = " ".join(str(a.value) for a in result.attributes)
                desc = await describer.describe(
                    sid, doc.name, [asdict(a) for a in result.attributes], doc.content_hash)
                text = f"{doc.name} {values}".strip()
                if desc:
                    text = f"{text}\n{desc}"
                return await emb.embed_product(sid, doc.name, text, doc.content_hash)

        results: list[bool] = []
        step = concurrency * 4
        for i in range(0, len(ids), step):
            results += await asyncio.gather(*[one(s) for s in ids[i:i + step]])
        return sum(results), len(ids)
