"""소스 상품을 강화 임베딩한다(C 백필, 동시성, 캐시).

각 상품에 LLM 설명(한/영)을 붙여 임베딩 텍스트를 강화한다. content-hash 게이팅으로
재실행·미변경분은 재호출하지 않는다(캐시 안전). ingest_products의 동시성 버전 —
대규모 초기 강화용(LLM 설명·임베딩 호출을 병렬화). 수십만 규모는 Batch API가 후속.

--sample-diverse: 상품 유형 키워드로 계층 샘플링해 다양한 유형(플라스크·피펫·비커 등)이
고르게 들어가게 한다(카탈로그가 소수 대형 카테고리로 편향돼도 희소 유형 누락 방지).
데모/평가용 대표 샘플에 쓴다. --reset: 적재 전 임베딩·설명 테이블을 비운다.

    docker compose run --rm api python manage.py embed_products [--concurrency 8] [--limit N]
    docker compose run --rm api python manage.py embed_products --sample-diverse --reset --limit 400
"""
import asyncio
import os

from django.core.management.base import BaseCommand

from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.embeddings.describe import DescriptionStore, build_describer
from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider
from apps.extraction.pdf import build_pdf_extractor
from apps.sync.runner import IngestRunner, build_extractor


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")

# 실험·연구 장비 대표 상품 유형(상품명 영문 기준) — 다양성 샘플링용.
LAB_TYPE_KEYWORDS = [
    "flask", "volumetric flask", "pipette", "pipette tip", "beaker", "cylinder",
    "graduated cylinder", "stirrer", "magnetic stirrer", "hot plate", "bottle", "wash bottle",
    "tube", "test tube", "funnel", "filter", "syringe", "vial", "cryogenic vial", "dish",
    "petri dish", "rack", "tube rack", "thermometer", "balance", "centrifuge", "forceps",
    "crucible", "burette", "spatula", "vortex", "shaker", "cover glass", "slide glass",
    "microscope slide", "immersion oil", "refractometer", "desiccator", "watch glass",
    "dispenser", "dropper", "polycarbonate", "platinum", "tungsten", "label", "bag",
]


class Command(BaseCommand):
    help = "소스 상품을 LLM 설명으로 강화 임베딩한다(C 백필, 동시성, 캐시)."

    def add_arguments(self, parser):
        parser.add_argument("--concurrency", type=int, default=8)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--sample-diverse", action="store_true",
            help="유형 키워드 계층 샘플링(다양한 유형 커버). --limit이 목표 개수(기본 400).",
        )
        parser.add_argument(
            "--by-category", action="store_true",
            help="세부카테고리(ca_id)마다 --per-category개씩 — 모든 카테고리 완전 커버(커버리지 공백 없음).",
        )
        parser.add_argument("--per-category", type=int, default=3)
        parser.add_argument(
            "--reset", action="store_true", help="적재 전 임베딩·설명 테이블을 비운다.",
        )

    def handle(self, *args, **options):
        new, total = asyncio.run(self._run(
            options["concurrency"], options["limit"], options["sample_diverse"],
            options["reset"], options["by_category"], options["per_category"],
        ))
        self.stdout.write(self.style.SUCCESS(f"enriched-embedded {new} new / {total} products"))

    async def _run(self, concurrency, limit, sample_diverse, reset, by_category=False, per_category=3):
        connector = YoungcartMySQLConnector.from_env()
        emb = EmbeddingStore(OpenAIEmbeddingProvider())
        describer = build_describer()
        pdf_ex = build_pdf_extractor() if _env_bool("INGEST_PDF") else None
        if reset:  # 기존(편향) 샘플 제거 후 새로 채운다
            await emb.reset()
            await DescriptionStore().reset()
        await emb.ensure()        # 동시 백필 전 테이블·인덱스 선생성(CREATE TABLE 레이스 방지)
        await describer.ensure()

        # id 수집: 카테고리 계층(완전 커버) > 키워드 다양성 > 세션 스트리밍.
        if by_category:
            ids = await connector.sample_by_category_ids(per_category)
        elif sample_diverse:
            target = limit or 400
            per_kw = max(5, target // len(LAB_TYPE_KEYWORDS))
            ids = await connector.sample_diverse_ids(LAB_TYPE_KEYWORDS, per_kw, target)
        else:
            async with connector.session():
                ids = [sid async for sid in connector.iter_product_ids(limit=limit)]

        # 적재 로직은 IngestRunner에 위임(assemble→추출→PDF 강화→설명→임베딩, 게이팅 포함).
        runner = IngestRunner(
            connector, build_extractor(use_llm=False),
            embedder=emb, describer=describer, pdf_extractor=pdf_ex,
        )
        sem = asyncio.Semaphore(concurrency)

        async def one(sid: str) -> bool:
            async with sem:
                status = await runner.apply(sid)  # 세션 밖 → 자체 커넥션(동시 안전)
                return status in ("created", "updated")

        results: list[bool] = []
        step = concurrency * 4
        for i in range(0, len(ids), step):
            results += await asyncio.gather(*[one(s) for s in ids[i:i + step]])

        # 적재 완료 후 HNSW 근사인덱스 빌드(대규모 검색 가속). populated 테이블 일괄
        # 빌드가 증분보다 빠르다 — 소규모에선 플래너가 안 써도 무해, 61만에서 위력.
        built = await emb.ensure_ann_index()
        if built:
            self.stdout.write(self.style.SUCCESS("HNSW ANN 인덱스 빌드 완료"))
        return sum(results), len(ids)
