"""이슈 26 B — 실제 OpenAI 속성 추출을 N건에 돌리고 토큰 사용량을 측정한다.

상품 텍스트에서 Functional Attribute를 추출해 그래프에 저장하고, 마지막에 chat 토큰
사용량을 출력한다. (임베딩은 제거됨, ADR-0010)

    docker compose run --rm \
      -e SOURCE_DB_HOST=real-source-db -e SOURCE_DB_USER=root \
      -e SOURCE_DB_PASSWORD=root -e SOURCE_DB_NAME=kolabshop \
      api python run_b.py 100
"""
import asyncio
import os
import sys
from dataclasses import asdict

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.agent.openai_client import OpenAILLM, get_usage, reset_usage  # noqa: E402
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector  # noqa: E402
from apps.extraction.extractor import AttributeExtractor  # noqa: E402
from apps.graph.store import GraphStore  # noqa: E402


async def main(limit: int):
    connector = YoungcartMySQLConnector.from_env()
    store = GraphStore()
    extractor = AttributeExtractor(OpenAILLM())
    reset_usage()

    n = 0
    extract_fail = 0
    async for source_id in connector.iter_product_ids(limit=limit):
        doc = await connector.assemble(source_id)
        if doc is None:
            continue
        try:
            result = await extractor.extract(doc)
            await store.set_attributes(source_id, [asdict(a) for a in result.attributes])
        except Exception as exc:  # noqa: BLE001
            extract_fail += 1
            print("extract fail", source_id, repr(exc)[:80])
        n += 1

    usage = get_usage()
    print("=== B RESULT ===")
    print(f"products_processed={n} extract_fail={extract_fail}")
    print(f"chat_in_tokens={usage['chat_in']} chat_out_tokens={usage['chat_out']}")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
