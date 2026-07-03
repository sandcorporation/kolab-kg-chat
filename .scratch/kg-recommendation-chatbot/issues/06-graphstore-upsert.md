# 06 — GraphStore: 노드·엣지 멱등 upsert

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

Postgres+AGE+pgvector 위의 **GraphStore 딥모듈**(ADR-0003). 그래프 스키마: `Product`/`Variant` 노드 + `HAS_VARIANT` 엣지(추후 Application/Condition/Compatibility 확장). 모든 쓰기는 **소스 PK 기준 멱등 upsert**(ADR-0008) — 같은 키 재실행 시 노드/엣지 중복 생성 금지.

## Acceptance criteria

- [ ] `upsert_product(ProductDocument)` → Product + Variant 노드 + HAS_VARIANT 엣지 생성
- [ ] 같은 source_id로 두 번 upsert → 노드 1개(중복 없음), 속성은 최신값
- [ ] Variant는 variant_key 기준 멱등
- [ ] 삭제된 source_id upsert/삭제 시 그래프에서 제거됨
- [ ] 통합 테스트: AGE 컨테이너 대상 read-back. prior art: embed-chat `test_graph_store_pg.py`

## Blocked by

- `02-postgres-age-pgvector.md`
