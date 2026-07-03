"""지식그래프 AGE 속성 인덱스를 멱등 생성/점검한다(대규모 적재·조회 필수).

    docker compose ... run --rm api python manage.py ensure_indexes
"""
import asyncio

from django.core.management.base import BaseCommand

from apps.graph.store import GraphStore


class Command(BaseCommand):
    help = "지식그래프 AGE 속성 인덱스를 멱등 생성한다(Product.source_id 등)."

    def handle(self, *args, **options):
        asyncio.run(GraphStore().ensure_indexes())
        self.stdout.write(self.style.SUCCESS("indexes ensured on knowledge_graph"))
