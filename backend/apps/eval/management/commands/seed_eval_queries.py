"""계층화 평가 쿼리셋을 eval_query 테이블에 적재한다(이슈 05).

    docker compose run --rm api python manage.py seed_eval_queries
"""
import asyncio
from collections import Counter

from django.core.management.base import BaseCommand

from apps.eval.queries import QUERIES, EvalQueries


class Command(BaseCommand):
    help = "계층화 평가 쿼리셋을 적재한다."

    def handle(self, *args, **options):
        n, strata = asyncio.run(self._run())
        self.stdout.write(self.style.SUCCESS(f"seeded {n} queries  strata={dict(strata)}"))

    async def _run(self):
        q = EvalQueries()
        await q.reset()
        await q.seed(QUERIES)
        strata = Counter(s for _, _, s in QUERIES)
        return len(QUERIES), strata
