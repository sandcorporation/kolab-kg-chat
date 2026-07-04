"""실 카탈로그에서 평가 코퍼스를 선별하고(계층 태그) 선택적으로 eval_graph에 적재한다(이슈 00).

    docker compose run --rm \
      -e SOURCE_DB_HOST=real-source-db -e SOURCE_DB_USER=root \
      -e SOURCE_DB_PASSWORD=root -e SOURCE_DB_NAME=kolabshop \
      api python manage.py build_eval_corpus --ingest
"""
import asyncio
from collections import Counter

import aiomysql
from django.core.management.base import BaseCommand

from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.eval.corpus import EvalCorpus
from apps.graph.store import GraphStore
from apps.sync.runner import IngestRunner, StructuredFieldInfoExtractor

# 계층별 균형 풀 — 그냥 상위 N을 뽑으면 structured에 편향돼 vision/semantic 차이를 못 건드린다.
# 각 계층을 타깃 쿼리로 뽑아 합쳐, 코퍼스가 차이를 드러낼 케이스를 실제로 담게 한다(이슈 00).
_HAS_FI = ("EXISTS(SELECT 1 FROM g5_shop_item_option o "
           "JOIN g5_shop_item_field_info f ON f.material_number = o.io_catno "
           "WHERE o.it_id = i.it_id)")

# 한/영 혼합 이름(시맨틱 미스매치 후보)
MIXED_SQL = f"""
SELECT i.it_id, i.it_name, LENGTH(i.it_explan) AS explan_len, i.ca_id, {_HAS_FI} AS has_field_info
FROM g5_shop_item i
WHERE i.it_use = 1 AND i.it_img1 <> ''
  AND i.it_name REGEXP '[가-힣]' AND i.it_name REGEXP '[A-Za-z]'
LIMIT %s
"""

# 스펙이 이미지에만(짧은 설명 + field_info 없음) + kolabshop 호스팅 이미지(도달 가능).
# it_img1이 절대 URL(http*)이면 외부 CDN(Sigma 등, fetch 불가)이라 제외 → vision이 실제로 동작.
IMAGE_ONLY_SQL = """
SELECT c.it_id, c.it_name, LENGTH(c.it_explan) AS explan_len, c.ca_id, 0 AS has_field_info
FROM (
  SELECT it_id, it_name, it_explan, ca_id FROM g5_shop_item i
  WHERE it_use = 1 AND it_img1 <> '' AND it_img1 NOT LIKE 'http%%'
    AND it_img1 NOT LIKE '%%no-image%%' AND LENGTH(it_explan) < 80 LIMIT 4000
) c
WHERE NOT EXISTS(
  SELECT 1 FROM g5_shop_item_option o
  JOIN g5_shop_item_field_info f ON f.material_number = o.io_catno WHERE o.it_id = c.it_id)
LIMIT %s
"""

# 구조 스펙 풍부(field_info 보유)
STRUCTURED_SQL = f"""
SELECT i.it_id, i.it_name, LENGTH(i.it_explan) AS explan_len, i.ca_id, 1 AS has_field_info
FROM g5_shop_item i
WHERE i.it_use = 1 AND i.it_img1 <> '' AND {_HAS_FI}
LIMIT %s
"""


class Command(BaseCommand):
    help = "실 카탈로그에서 평가 코퍼스를 선별(계층 태그)하고 선택적으로 eval_graph에 적재한다."

    def add_arguments(self, parser):
        parser.add_argument("--target", type=int, default=250, help="코퍼스 크기")
        parser.add_argument("--per-stratum", type=int, default=140, help="계층별 풀 크기")
        parser.add_argument("--seed", type=int, default=0)
        parser.add_argument("--ingest", action="store_true", help="선별 상품을 eval_graph에 구조 적재")

    def handle(self, *args, **options):
        asyncio.run(self._run(options))

    async def _run(self, o):
        connector = YoungcartMySQLConnector.from_env()
        k = o["per_stratum"]
        rows = []
        conn = await connector._connect()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                for sql in (MIXED_SQL, IMAGE_ONLY_SQL, STRUCTURED_SQL):
                    await cur.execute(sql, (k,))
                    rows += await cur.fetchall()
        finally:
            conn.close()

        by_id = {}  # it_id 중복 제거(계층 겹침)
        for r in rows:
            by_id.setdefault(r["it_id"], {
                "source_id": r["it_id"], "name": r["it_name"], "explan_len": r["explan_len"] or 0,
                "has_image": True, "has_field_info": bool(r["has_field_info"]), "ca_id": r["ca_id"],
            })
        candidates = list(by_id.values())
        corpus = EvalCorpus()
        await corpus.reset()
        n = await corpus.build(candidates, target=o["target"], seed=o["seed"])

        picked = await corpus.list()
        strata = Counter(t for p in picked for t in p["tags"])
        self.stdout.write(f"corpus: {n} products (pool {len(candidates)})  strata={dict(strata)}")

        if o["ingest"]:
            ids = [p["source_id"] for p in picked]
            store = GraphStore(graph_name="eval_graph")
            await store.reset()  # eval_graph = 코퍼스와 정확히 일치(공정한 검색 범위)
            await store.ensure_indexes()
            runner = IngestRunner(store, connector, StructuredFieldInfoExtractor())
            async with connector.session():
                async with store.batch():
                    for source_id in ids:
                        await runner.apply(source_id)
            self.stdout.write(self.style.SUCCESS(f"ingested {len(ids)} products into eval_graph"))
            await self._create_source_view(connector, ids)
            self.stdout.write(self.style.SUCCESS("created eval_items view (corpus-scoped) in source"))

    async def _create_source_view(self, connector, ids):
        """config 1(text-to-SQL)이 코퍼스만 보도록 소스에 eval_items 뷰를 만든다."""
        id_list = ",".join("'" + str(i).replace("'", "''") + "'" for i in ids)
        view_sql = f"""
        CREATE OR REPLACE VIEW eval_items AS
        SELECT i.it_id, i.it_name, i.it_explan, i.it_brand, i.ca_id,
          (SELECT GROUP_CONCAT(CONCAT_WS(' ', f.product_description, f.purity, f.cas_number,
             f.molecular_formula, f.storage, f.boiling_point, f.melting_point) SEPARATOR ' | ')
           FROM g5_shop_item_field_info f WHERE f.it_id = i.it_id) AS specs
        FROM g5_shop_item i WHERE i.it_id IN ({id_list})
        """
        conn = await connector._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(view_sql)
            await conn.commit()
        finally:
            conn.close()
