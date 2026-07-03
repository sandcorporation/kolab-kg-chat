# 04 — 운영/문서 정리 (env·README·ADR)

Status: done — .env.example EMBEDDING_MODEL, README 적재-임베딩·백필·semantic_search 반영, 동작방식 벡터 문구 ADR-0012로 갱신.

## Parent
`.scratch/reintroduce-embeddings/PRD.md`

## What to build

임베딩 재도입에 맞춘 운영/문서 정리. 임베딩 모델 환경변수(`EMBEDDING_MODEL`, 기본 text-embedding-3-small)를 `.env.example`에 문서화. README 적재/동기화 절에 "적재 시 임베딩 + 백필 명령" 반영. 대규모 적재 시 임베딩이 인제스트 시간·비용을 늘린다는 주의. ADR-0012 상태를 done으로 갱신.

## Acceptance criteria

- [ ] `.env.example`에 `EMBEDDING_MODEL`(및 비용 주석) 추가
- [ ] README에 임베딩 적재·백필·semantic_search 반영
- [ ] 스택이 정상 기동·헬스체크 통과(회귀 없음)

## Blocked by
- 01·02·03 (구현 완료 후 문서화)
