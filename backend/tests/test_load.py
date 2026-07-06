"""이슈 25 — PG 풀링으로 100 동시 요청 처리 (커넥션 한도 미초과)."""
import asyncio

from apps.core.db import make_pool


async def test_pool_handles_100_concurrent_requests():
    pool = make_pool(max_size=10)
    await pool.open()
    try:
        async def query():
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    return (await cur.fetchone())[0]

        results = await asyncio.gather(*[query() for _ in range(100)])
        # 풀(최대 10)로 100 동시 요청이 모두 성공 — 큐잉으로 처리
        assert results == [1] * 100
    finally:
        await pool.close()
