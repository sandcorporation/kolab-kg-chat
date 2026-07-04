"""계층화 평가 쿼리셋 (이슈 05).

코퍼스 실제 상품에 근거해 작성(답 존재). 계층 태그로 '어디서 어느 config가 이기는지' 진단.
- keyword: 상품명 직접 매칭(모든 config 기본기)
- structured: 스펙/속성으로 답(field_info를 쓰는 2/3/4 유리 가능)
- semantic: 유의어·서술형(상품명 키워드 미스매치 → 임베딩 config4 유리 가능)

주의: 이 코퍼스는 vision 커버리지가 미미하고(외부 CDN·상품사진) compatibility 엣지가 없어
해당 두 계층은 판별력이 없어 제외했다(정직한 데이터 제약).
"""
from __future__ import annotations

from apps.core.db import connect

# (query_id, text, stratum) — 실제 코퍼스 상품에 답이 있도록 작성
QUERIES: list[tuple[str, str, str]] = [
    # ── keyword: 상품명 직접 ──
    ("kw01", "메스플라스크 추천해줘", "keyword"),
    ("kw02", "원형 커버글라스 필요해", "keyword"),
    ("kw03", "볼텍스 믹서 있어?", "keyword"),
    ("kw04", "슬라이드글라스 랙 찾아줘", "keyword"),
    ("kw05", "cryogenic vials", "keyword"),
    ("kw06", "narrow mouth wash bottle", "keyword"),
    ("kw07", "immersion oil 추천", "keyword"),
    # ── structured: 스펙/속성 ──
    ("st01", "고순도 알루미늄-마그네슘 합금", "structured"),
    ("st02", "구리와 니켈로 된 저항 합금", "structured"),
    ("st03", "폴리카보네이트 재질 랩웨어", "structured"),
    ("st04", "유리 재질 피펫 팁", "structured"),
    ("st05", "수평형 진탕기(horizontal shaker)", "structured"),
    ("st06", "동결 보존용 바이알", "structured"),
    ("st07", "굴절률 측정용 표준 액체", "structured"),
    ("st08", "저합금강 표준물질(NIST)", "structured"),
    ("st09", "백금(Pt) 금속 시료", "structured"),
    ("st10", "진공 증착용 텅스텐 보트", "structured"),
    # ── semantic: 유의어·서술형(키워드 미스매치) ──
    ("se01", "얇고 둥근 유리 덮개", "semantic"),
    ("se02", "공기 시료를 담는 봉투", "semantic"),
    ("se03", "액체를 정확히 옮기는 실험 도구", "semantic"),
    ("se04", "가루 시약을 뜨는 작은 주걱", "semantic"),
    ("se05", "시험관을 담아두는 금속 바구니", "semantic"),
    ("se06", "현미경 렌즈에 쓰는 침용 기름", "semantic"),
    ("se07", "시료를 얼려 장기 보관하는 작은 병", "semantic"),
    ("se08", "위험물질 경고를 붙이는 라벨", "semantic"),
    ("se09", "용액을 흔들어 섞는 실험 장비", "semantic"),
    ("se10", "은백색 전이금속 소재", "semantic"),
    # ── compatibility: 호환/부속(그래프 다중홉 강점) ──
    ("cp01", "Nichipet Eco 피펫에 맞는 유리 팁 추천", "compatibility"),
    ("cp02", "Nichipet Eco pipette와 함께 쓰는 소모품", "compatibility"),
    ("cp03", "다중 튜브 랙에 넣을 극저온 바이알", "compatibility"),
    ("cp04", "튜브 홀더에 호환되는 바이알", "compatibility"),
]


class EvalQueries:
    def __init__(self, connect_factory=connect, table: str = "eval_query"):
        self._connect = connect_factory
        assert table.replace("_", "").isalnum(), "table must be a safe identifier"
        self._table = f"public.{table}"

    async def _ensure(self, cur) -> None:
        await cur.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            " query_id text PRIMARY KEY, text text NOT NULL, stratum text NOT NULL)"
        )

    async def reset(self) -> None:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(f"DROP TABLE IF EXISTS {self._table}")
                await self._ensure(cur)
        finally:
            await conn.close()

    async def seed(self, queries) -> int:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                for qid, text, stratum in queries:
                    await cur.execute(
                        f"INSERT INTO {self._table} (query_id, text, stratum) VALUES (%s,%s,%s) "
                        "ON CONFLICT (query_id) DO UPDATE SET text=EXCLUDED.text, stratum=EXCLUDED.stratum",
                        (qid, text, stratum),
                    )
        finally:
            await conn.close()
        return len(list(queries))

    async def list(self) -> list[dict]:
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await self._ensure(cur)
                await cur.execute(f"SELECT query_id, text, stratum FROM {self._table} ORDER BY query_id")
                rows = await cur.fetchall()
        finally:
            await conn.close()
        return [{"query_id": r[0], "text": r[1], "stratum": r[2]} for r in rows]
