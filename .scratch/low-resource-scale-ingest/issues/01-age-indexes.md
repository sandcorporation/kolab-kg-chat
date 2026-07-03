# 01 — AGE 속성 인덱스 멱등 생성

Status: done

## Parent
`.scratch/low-resource-scale-ingest/PRD.md`

## What to build

GraphStore가 그래프 셋업 시 멱등으로 btree 인덱스를 생성한다: `Product.source_id`(필수), `Variant.variant_key`, `Attribute.name`, `Attribute.value`. AGE 정점 테이블의 properties 접근 표현식 인덱스로, `MERGE/MATCH {source_id}`·속성 필터를 시퀀셜 스캔에서 인덱스 조회로 바꾼다. 관리 명령 `ensure_indexes`로도 실행 가능해야 한다.

## Acceptance criteria

- [ ] 그래프가 준비되면 위 4개 인덱스가 존재한다(pg 카탈로그로 확인)
- [ ] 여러 번 호출해도 안전(멱등)
- [ ] `manage.py ensure_indexes`가 인덱스를 보장한다
- [ ] 인덱스 존재 하에 upsert/조회 동작이 기존과 동일(회귀 없음)

## Blocked by
None - can start immediately
