"""이슈 02 — Postgres + AGE + pgvector 통합 테스트.

실제 DB 컨테이너 대상. age로 cypher가 돌고, pgvector로 거리 정렬이 되며,
확장 생성이 멱등임을 검증한다.
"""
import psycopg

from apps.core.db import connect, get_database_url


async def test_age_runs_cypher():
    conn = await connect()
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM ag_catalog.ag_graph WHERE name = 'health_check'")
            (cnt,) = await cur.fetchone()
            if cnt == 0:
                await cur.execute("SELECT create_graph('health_check')")
            await cur.execute("SELECT * FROM cypher('health_check', $$ RETURN 1 $$) AS (v agtype)")
            row = await cur.fetchone()
            assert row is not None
    finally:
        await conn.close()


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


async def test_extension_creation_is_idempotent():
    conn = await psycopg.AsyncConnection.connect(get_database_url(), autocommit=True)
    try:
        async with conn.cursor() as cur:
            await cur.execute("CREATE EXTENSION IF NOT EXISTS age")
            await cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    finally:
        await conn.close()
