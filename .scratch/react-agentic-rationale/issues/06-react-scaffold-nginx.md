# 06 — React 스캐폴드(Vite+TS) + nginx 멀티스테이지 서빙

Status: done — `frontend/`(Vite+TS) + `nginx/Dockerfile`(멀티스테이지) + compose 재배선, 이미지 빌드/서빙 검증.

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

`frontend/` Vite + React + TypeScript 앱을 만들고, **nginx 멀티스테이지 빌드**(node로 빌드 → dist를 nginx로)로 `/`에서 서빙한다(기존 바닐라 widget.html 대체). `/chat`·`/recommend`·`/health`·`/openapi.json`은 api로 프록시(단일 엔드포인트 유지, SSE 버퍼링 off).

## Acceptance criteria

- [ ] `frontend/` Vite+React+TS 앱 생성, 최소 챗 셸 렌더
- [ ] nginx 멀티스테이지 Dockerfile로 React dist 빌드·서빙
- [ ] `http://localhost/` → React 앱 로드(위젯 대체)
- [ ] `/health` 등 API가 nginx 통해 정상 프록시
- [ ] `docker compose up`으로 단일 엔드포인트 동작

## Blocked by
None - can start immediately
