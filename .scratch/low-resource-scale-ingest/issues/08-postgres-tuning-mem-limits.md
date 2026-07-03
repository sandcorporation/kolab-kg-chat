# 08 — Postgres 2GB 튜닝 + compose mem_limit

Status: done

## Parent
`.scratch/low-resource-scale-ingest/PRD.md`

## What to build

저사양(2GB) 안정화. db 이미지에 2GB용 `postgresql.conf`(예: shared_buffers ~256MB, work_mem 작게, maintenance_work_mem 상향 — 인덱스 빌드용). compose 서비스별 `mem_limit`로 예산 배분(db/api/worker). prod 조합에 적용. 대량 적재 세션의 `synchronous_commit=off`는 러너(06)에서.

## Acceptance criteria

- [ ] db가 2GB용 설정으로 뜬다(설정 적용 확인)
- [ ] prod compose 서비스에 mem_limit가 설정된다
- [ ] 스택이 정상 기동·헬스체크 통과(회귀 없음)

## Blocked by
None - can start immediately (튜닝은 독립, 세션 설정은 06과 연동)
