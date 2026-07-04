"""eval_graph에 자연스러운 COMPATIBLE_WITH 엣지를 넣는다(그래프 다중홉 강점 검증용, (b)).

코퍼스의 실제 호환 쌍:
- Nichipet Eco 피펫 → Nichipet 유리 팁(Eco용)
- 다중 튜브 랙 / 튜브 홀더 → 극저온 바이알

    docker compose run --rm api python manage.py seed_eval_compat
"""
import asyncio

from django.core.management.base import BaseCommand

from apps.graph.store import GraphStore


def _ids(products, *needles):
    return [p["source_id"] for p in products
            if all(n.lower() in p["name"].lower() for n in needles)]


class Command(BaseCommand):
    help = "eval_graph에 자연스러운 호환 엣지를 넣는다."

    def handle(self, *args, **options):
        n = asyncio.run(self._run())
        self.stdout.write(self.style.SUCCESS(f"added {n} COMPATIBLE_WITH edges to eval_graph"))

    async def _run(self):
        store = GraphStore(graph_name="eval_graph")
        products = await store.list_products()

        eco_pipettes = _ids(products, "eco", "pipette")
        glass_tips = _ids(products, "glass tip", "eco")
        racks = _ids(products, "multi-tube") + _ids(products, "tube holder")
        vials = _ids(products, "cryogenic", "vial")

        edges = 0
        for pipette in eco_pipettes:          # 피펫 → 팁
            for tip in glass_tips:
                await store.add_compatibility(pipette, tip)
                edges += 1
        for rack in racks:                     # 랙/홀더 → 바이알
            for vial in vials:
                await store.add_compatibility(rack, vial)
                edges += 1
        self.stdout.write(
            f"  pipettes={len(eco_pipettes)} tips={len(glass_tips)} "
            f"racks={len(racks)} vials={len(vials)}"
        )
        return edges
