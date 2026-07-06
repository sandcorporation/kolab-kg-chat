"""ADR-0016 — Postgres + pgvector + pg_trgm 통합 테스트.

실제 DB 컨테이너 대상. pgvector로 거리 정렬이 되고, pg_trgm이 있으며, 확장 생성이 멱등임을
검증한다(Apache AGE는 C로 제거됨).
"""
import psycopg

from apps.core.db import connect, get_database_url


async def test_pgvector_knn_orders_by_distance():
    conn = await connect()
    try:
        async with conn.cursor() as cur:
            await cur.execute("DROP TABLE IF EXISTS _vtest")
            await cur.execute("CREATE TABLE _vtest (id int, embedding vector(3))")
            await cur.execute(
                "INSERT INTO _vtest (id, embedding) VALUES (1, '[1,0,0]'), (2, '[0,1,0]')"
            )
            await cur.execute("SELECT id FROM _vtest ORDER BY embedding <-> '[0.9,0,0]' LIMIT 1")
            (nearest,) = await cur.fetchone()
            assert nearest == 1
            await cur.execute("DROP TABLE _vtest")
    finally:
        await conn.close()


async def test_pg_trgm_available_for_keyword_search():
    conn = await connect()
    try:
        async with conn.cursor() as cur:
            # 키워드 검색(name ILIKE) 고속화에 쓰는 trigram 유사도 함수가 동작한다.
            await cur.execute("SELECT similarity('flask', 'flasks')")
            (sim,) = await cur.fetchone()
            assert sim > 0
    finally:
        await conn.close()


async def test_extension_creation_is_idempotent():
    conn = await psycopg.AsyncConnection.connect(get_database_url(), autocommit=True)
    try:
        async with conn.cursor() as cur:
            await cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    finally:
        await conn.close()
