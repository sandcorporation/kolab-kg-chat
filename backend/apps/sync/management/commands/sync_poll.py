"""소스 DB를 폴링해 변경분을 강화 임베딩에 반영한다(폴링 워커, 저부하 증분 우선).

평소엔 it_update_time 증분(바뀐 상품만) → watermark 전진. 저빈도로 전체 재조정을 돌려
하드 삭제·드리프트를 보정한다(ADR-0008). it_update_time이 없으면 재조정으로 폴백.
실시간이 필요하면 CDC로 대체(ADR-0002).

    python manage.py sync_poll --once                 # 증분 1회(크론)
    python manage.py sync_poll --once --reconcile      # 재조정 1회(삭제 보정, 야간 크론)
    python manage.py sync_poll --interval 3600         # 워커 루프(주기적 재조정 포함)
"""
import asyncio
import os

from django.core.management.base import BaseCommand

from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.sync.runner import IngestRunner, build_extractor


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


class Command(BaseCommand):
    help = "소스 DB를 폴링해 변경분을 강화 임베딩에 반영한다(증분 + 주기적 재조정)."

    def add_arguments(self, parser):
        # 기본값은 .env로 제어(자동 실행 워커라 CLI를 못 주는 경우가 많다). CLI가 우선.
        parser.add_argument("--once", action="store_true", help="한 번만 폴링하고 종료(크론용)")
        parser.add_argument(
            "--interval", type=int, default=int(os.environ.get("SYNC_INTERVAL", "3600")),
            help="루프 모드 폴링 주기(초). env SYNC_INTERVAL.",
        )
        parser.add_argument("--reconcile", action="store_true", help="이번 실행을 전체 재조정으로")
        parser.add_argument(
            "--reconcile-every", type=int,
            default=int(os.environ.get("SYNC_RECONCILE_EVERY", "24")),
            help="루프에서 N 사이클마다 재조정(0=하지 않음). env SYNC_RECONCILE_EVERY.",
        )
        parser.add_argument(
            "--llm", action="store_true", default=_env_bool("SYNC_LLM"),
            help="변경 상품을 LLM으로 재추출(비용 발생). env SYNC_LLM.",
        )

    def handle(self, *args, **options):
        try:
            asyncio.run(self._run(options))
        except KeyboardInterrupt:
            self.stdout.write("stopped.")

    async def _run(self, opts):
        from apps.embeddings.describe import build_describer
        from apps.embeddings.store import EmbeddingStore, OpenAIEmbeddingProvider
        from apps.extraction.pdf import build_pdf_extractor

        pdf_ex = build_pdf_extractor() if _env_bool("INGEST_PDF") else None
        runner = IngestRunner(
            YoungcartMySQLConnector.from_env(), build_extractor(opts["llm"]),
            embedder=EmbeddingStore(OpenAIEmbeddingProvider()),  # 변경분 임베딩 + content-hash 인덱스
            describer=build_describer(),  # Route C: LLM 설명으로 임베딩 강화
            pdf_extractor=pdf_ex,         # INGEST_PDF면 변경분 PDF로 설명 강화
        )
        cycle = 0
        every = opts["reconcile_every"]
        while True:
            if opts["reconcile"] or (every and cycle % every == 0):
                counts = await runner.sync_once()  # 전체 재조정
            else:
                counts = await runner.sync_incremental()
                if "incremental_unavailable" in counts:  # it_update_time 없음 → 폴백
                    counts = await runner.sync_once()
            self.stdout.write(f"sync: {counts or 'no changes'}")
            if opts["once"]:
                return
            cycle += 1
            await asyncio.sleep(opts["interval"])
