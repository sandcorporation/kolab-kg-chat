"""이슈 05 — 비전 비용 파일럿. 실제 gpt-4o(-mini) vision으로 스펙 이미지에서 속성 추출.

이미지 URL은 OpenAI 서버가 fetch하므로 공개 접근 가능해야 한다(상대경로 → 절대 URL).

    docker compose run --rm \
      -e SOURCE_DB_HOST=real-source-db -e SOURCE_DB_USER=root \
      -e SOURCE_DB_PASSWORD=root -e SOURCE_DB_NAME=kolabshop \
      -e OPENAI_VISION_MODEL=gpt-4o-mini \
      api python run_vision_pilot.py 100
"""
import asyncio
import os
import sys
from dataclasses import asdict

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.agent.openai_client import OpenAIVisionClient, get_usage, reset_usage  # noqa: E402
from apps.connectors.base import SourceImage  # noqa: E402
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector  # noqa: E402
from apps.extraction.images import ImageAttributeExtractor, triage_spec_images  # noqa: E402
from apps.graph.store import GraphStore  # noqa: E402

BASE = "https://www.kolabshop.com"


def absolutize(url: str) -> str:
    if url.startswith("http"):
        return url
    return BASE + (url if url.startswith("/") else "/" + url)


async def main(limit: int):
    connector = YoungcartMySQLConnector.from_env()
    store = GraphStore()
    extractor = ImageAttributeExtractor(OpenAIVisionClient())
    reset_usage()

    seen = attempted = ok = fail = with_attrs = images_sent = 0
    sample = None
    async for source_id in connector.iter_product_ids(limit=limit):
        doc = await connector.assemble(source_id)
        if doc is None or not doc.images:
            continue
        seen += 1
        images = [SourceImage(absolutize(i.url), i.position, i.source) for i in doc.images]
        images_sent += len(triage_spec_images(images))
        attempted += 1
        try:
            result = await extractor.extract("glassware_consumable", images)
        except Exception as exc:  # noqa: BLE001
            fail += 1
            print("vision fail", source_id, repr(exc)[:70])
            continue
        ok += 1
        if result.attributes:
            await store.upsert_product(doc)
            await store.set_attributes(source_id, [asdict(a) for a in result.attributes])
            with_attrs += 1
            if sample is None:
                sample = (source_id, doc.name[:45],
                          [(a.name, a.value, a.provenance) for a in result.attributes[:5]])

    u = get_usage()
    print("=== VISION PILOT ===")
    print(f"with_images={seen} attempted={attempted} ok={ok} fail={fail} with_attrs={with_attrs}")
    print(f"images_sent_to_vision={images_sent}")
    print(f"vision chat_in={u['chat_in']} chat_out={u['chat_out']}")
    print("sample:", sample)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
