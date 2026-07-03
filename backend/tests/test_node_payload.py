"""이슈 02 — Product 노드에서 description 저장 제거(대규모 디스크 절감)."""
import json

from apps.core.db import connect
from apps.connectors.youngcart_mysql import YoungcartMySQLConnector
from apps.graph.store import GraphStore


async def _node_props(graph: str, sid: str) -> dict:
    conn = await connect()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT * FROM cypher('{graph}', $$ MATCH (p:Product {{source_id: '{sid}'}}) "
                "RETURN properties(p) $$) AS (p agtype)"
            )
            row = await cur.fetchone()
    finally:
        await conn.close()
    return json.loads(row[0])


async def test_upsert_does_not_store_description():
    store = GraphStore(graph_name="kg_test")
    await store.reset()
    doc = await YoungcartMySQLConnector.from_env().assemble("1548728629")
    assert doc.description_text  # 소스엔 설명이 있다
    await store.upsert_product(doc)

    props = await _node_props("kg_test", "1548728629")
    assert "description" not in props          # 그래프엔 저장하지 않는다
    assert props["name"].startswith("Volumetric Flask")  # 다른 필드는 유지
    assert "content_hash" in props
