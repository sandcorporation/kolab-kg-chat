# 19 — SSE 스트리밍 + 구조화 이벤트

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

읽기 경로를 **턴 단위 인라인 SSE 스트리밍**으로(ADR-0007). 질의 POST가 같은 연결로 답을 스트리밍한다. langgraph 에이전트가 그 async 요청 안에서 인라인 실행되며 `astream_events()` + custom `StreamWriter`로 이벤트를 흘린다. SSE 프레임 `event: {type}\ndata: {json}`, 타입: `token`/`recommendation`/`done`/`error`. Redis 미사용. Nginx `proxy_buffering off`.

## Acceptance criteria

- [ ] `POST /api/chat`(스트리밍) → 프로즈 `token` 델타가 실시간 흐름
- [ ] `recommendation` 이벤트로 상품+근거가 구조화 JSON으로 전달
- [ ] `done`/`error` 이벤트로 종료/오류 신호
- [ ] 에이전트가 웹 요청 안에서 인라인 실행(별도 워커/Redis 없음)
- [ ] 이벤트루프 비차단(async 클라이언트 전 구간)
- [ ] 통합 테스트: 가짜 LLM으로 이벤트 시퀀스 검증. prior art: embed-chat `test_chat_streaming.py`

## Blocked by

- `16-retriever-attribute-filter-composer.md`
