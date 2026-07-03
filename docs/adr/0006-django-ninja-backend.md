# 백엔드는 Django + Django Ninja로 한다 (FastAPI 번복)

플랜 3번은 FastAPI+uvicorn+async였다. 그러나 선행 프로젝트 `embed-chat`이 이미 **Django + langgraph + AGE-on-Postgres + OCR + SSE**로 동작하며(예: `test_graph_store_pg.py`, `test_entity_resolver.py`, `sse.py`), 우리 ADR-0001~0005의 패턴이 거기서 검증돼 있다. kolab-kg-chat은 이를 **포크하지 않고 새로 짓되 패턴만 차용**한다.

백엔드 프레임워크를 **Django + Django Ninja**로 한다. ASGI(uvicorn worker)로 구동하고 **전 구간 async**를 유지한다: async 뷰, 비동기 ORM(`aget`/`afilter`, Django 4.1+), AGE/pgvector raw SQL은 async 드라이버(psycopg3 async / asyncpg 풀), async OpenAI·redis 클라이언트.

이유: Django Ninja가 Pydantic·async·OpenAPI 생성(→ Orval, 플랜 6번)으로 FastAPI의 개발 경험을 Django 생태계 위에서 거의 그대로 제공하고, embed-chat의 검증된 스택과 정렬돼 패턴 재사용이 쉽다. 이전 ADR(0001~0005)은 프레임워크 무관이라 그대로 유효하다.

## 트레이드오프 / 결과

- **Django ORM은 동기가 기본** — 이것이 footgun이다. async 뷰에서 동기 ORM을 부르면 `sync_to_async`(스레드풀)로 조용히 넘어가 100 동시에서 직렬화·스레드풀 고갈을 일으킨다. 그래서 위 async 규율은 **선택이 아니라 전제**다. 깨지면 100-동시 인라인 스트리밍(ADR-0007)이 무너진다.
- FastAPI는 async 네이티브라 이 footgun이 없었으나, embed-chat 생태계 정렬·재사용을 위해 그 대가를 받아들인다.
- `embed-chat`의 `paddle_service`(PaddleOCR=고전 OCR)는 차용하지 않는다 — ADR-0005(비전 LLM)를 따른다.
