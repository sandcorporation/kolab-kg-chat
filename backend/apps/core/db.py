"""Async Postgres 접근 (ADR-0003·0006).

그래프 질의는 Django ORM이 아니라 async psycopg로 직접 한다. 이벤트 루프를
막지 않기 위해 동기 드라이버를 쓰지 않는다.
"""
import os

import psycopg


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "")


async def connect(*, autocommit: bool = True) -> psycopg.AsyncConnection:
    """AGE가 LOAD되고 search_path가 설정된 async 연결을 연다.

    AGE의 graph/cypher 함수는 세션마다 `LOAD 'age'`와 ag_catalog search_path를
    요구한다(미리 preload하지 않은 경우).
    """
    conn = await psycopg.AsyncConnection.connect(get_database_url(), autocommit=autocommit)
    async with conn.cursor() as cur:
        await cur.execute("LOAD 'age'")
        await cur.execute('SET search_path = ag_catalog, "$user", public')
    return conn


async def _configure_pool_connection(conn) -> None:
    """풀이 새 연결을 만들 때 AGE 로드 + search_path 설정(이슈 25)."""
    async with conn.cursor() as cur:
        await cur.execute("LOAD 'age'")
        await cur.execute('SET search_path = ag_catalog, "$user", public')


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
        kwargs={"autocommit": True},  # configure의 LOAD/SET이 트랜잭션을 열지 않게
        configure=_configure_pool_connection,
    )


async def check_db_health() -> dict:
    """DB 연결과 age·vector 확장 가용 여부를 보고한다(이슈 02 /health)."""
    url = get_database_url()
    if not url:
        return {"connected": False, "extensions": {"age": False, "vector": False}}
    try:
        conn = await psycopg.AsyncConnection.connect(url)
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT extname FROM pg_extension WHERE extname IN ('age', 'vector')"
                )
                names = {row[0] for row in await cur.fetchall()}
        finally:
            await conn.close()
        return {
            "connected": True,
            "extensions": {"age": "age" in names, "vector": "vector" in names},
        }
    except Exception:
        return {"connected": False, "extensions": {"age": False, "vector": False}}
