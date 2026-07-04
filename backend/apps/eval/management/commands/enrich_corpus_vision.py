"""코퍼스의 구조 스펙 부족(image_only) 상품에 vision 속성(llm_ocr)을 붙인다(이슈 03, 캐시).

    docker compose run --rm \
      -e SOURCE_DB_HOST=real-source-db -e SOURCE_DB_USER=root \
      -e SOURCE_DB_PASSWORD=root -e SOURCE_DB_NAME=kolabshop \
      -e OPENAI_VISION_MODEL=gpt-4o-mini \
      api python manage.py enrich_corpus_vision
"""
import asyncio

from django.core.management.base import BaseCommand

from apps.agent.openai_client import OpenAIVisionClient
from apps.agent.vision_cache import VisionCache
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.core.db import connect
from apps.eval.vision import CachingVisionClient, enrich_product_vision
from apps.extraction.images import ImageAttributeExtractor
from apps.graph.store import GraphStore


class Command(BaseCommand):
    help = "코퍼스의 image_only 상품에 vision 추출 속성(llm_ocr)을 병합한다(캐시)."

    def add_arguments(self, parser):
        parser.add_argument("--product-type", default="glassware_consumable")
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--delay", type=float, default=1.5, help="vision 호출 간 지연(초, 레이트리밋 완화)")

    def handle(self, *args, **options):
        asyncio.run(self._run(options))

    async def _run(self, o):
        conn = await connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT source_id FROM public.eval_corpus WHERE tags ? 'image_only'")
                ids = [r[0] for r in await cur.fetchall()]
        finally:
            await conn.close()
        if o["limit"]:
            ids = ids[: o["limit"]]

        connector = YoungcartMySQLConnector.from_env()
        store = GraphStore(graph_name="eval_graph")
        cache = VisionCache()
        total, enriched = 0, 0
        async with connector.session():
            for source_id in ids:
                doc = await connector.assemble(source_id)
                if doc is None:
                    continue
                client = CachingVisionClient(OpenAIVisionClient(), cache, source_id)
                added = None
                for attempt in range(4):  # 429 백오프 재시도
                    try:
                        added = await enrich_product_vision(
                            store, doc, ImageAttributeExtractor(client), o["product_type"]
                        )
                        break
                    except Exception as exc:  # noqa: BLE001
                        msg = str(exc).lower()
                        if ("429" in msg or "rate limit" in msg) and attempt < 3:
                            await asyncio.sleep(5 * (attempt + 1))
                            continue
                        self.stdout.write(f"  skip {source_id}: {str(exc)[:80]}")
                        break
                if added is not None:
                    total += added
                    enriched += 1 if added else 0
                await asyncio.sleep(o["delay"])  # 스로틀
        self.stdout.write(self.style.SUCCESS(
            f"vision: {enriched}/{len(ids)} products enriched, {total} llm_ocr attrs added"
        ))
