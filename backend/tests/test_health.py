"""이슈 01·02 — walking skeleton + DB/확장 헬스체크.

Django AsyncClient로 실제 URLconf(ASGI 스택)를 관통해 검증한다.
"""
from django.test import AsyncClient


async def test_health_reports_db_and_extensions():
    client = AsyncClient()
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"]["connected"] is True
    assert body["db"]["extensions"]["vector"] is True
    assert body["db"]["extensions"]["pg_trgm"] is True


async def test_openapi_schema_exposed():
    client = AsyncClient()
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Kolab KG Chat API"
