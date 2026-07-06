"""Async Postgres 접근 (ADR-0006/0016).

임베딩·설명 질의는 Django ORM이 아니라 async psycopg로 직접 한다(이벤트 루프를 막지
않도록 동기 드라이버를 쓰지 않는다). C(ADR-0016)로 Apache AGE를 제거해, 세션마다
`LOAD 'age'`·ag_catalog search_path를 설정할 필요가 없다 — pgvector·pg_trgm은 public에 있다.
"""
import os

import psycopg


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "")


async def connect(*, autocommit: bool = True) -> psycopg.AsyncConnection:
    """async 연결을 연다(pgvector·pg_trgm은 별도 세션 설정 불필요)."""
    return await psycopg.AsyncConnection.connect(get_database_url(), autocommit=autocommit)


def make_pool(max_size: int = 10, min_size: int = 1):
    """100 동시 요청을 유한한 커넥션으로 처리하는 async 풀(ADR-0007).

    챗당 커넥션을 열지 않고 풀에서 빌려 쓴다 → Postgres max_connections 초과 방지.
    """
    from psycopg_pool import AsyncConnectionPool

    return AsyncConnectionPool(
        get_database_url(),
        min_size=min_size,
        max_size=max_size,
        open=False,
        kwargs={"autocommit": True},
    )


async def check_db_health() -> dict:
    """DB 연결과 vector·pg_trgm 확장 가용 여부를 보고한다(/health)."""
    url = get_database_url()
    if not url:
        return {"connected": False, "extensions": {"vector": False, "pg_trgm": False}}
    try:
        conn = await psycopg.AsyncConnection.connect(url)
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')"
                )
                names = {row[0] for row in await cur.fetchall()}
        finally:
            await conn.close()
        return {
            "connected": True,
            "extensions": {"vector": "vector" in names, "pg_trgm": "pg_trgm" in names},
        }
    except Exception:
        return {"connected": False, "extensions": {"vector": False, "pg_trgm": False}}
