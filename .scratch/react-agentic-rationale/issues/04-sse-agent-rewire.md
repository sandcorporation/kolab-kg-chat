# 04 — SSE 스트림을 에이전트로 재배선

Status: done — `apps/agent/streaming.py`(agent_event_stream) + `runtime.py` + `views.py` 재배선, 테스트 `tests/test_sse_streaming.py` 통과.

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

`/chat` SSE를 RecommendationAgent로 재배선한다. 에이전트 astream_events에서 **근거 프로즈를 `token`으로 실시간** 흘리고, 에이전트가 고른 id를 ProductEnricher(01)로 카드화해 **`recommendation`** 이벤트로 보낸다. `clarification`/`done`/`error` 유지. 턴 단위 인라인·Redis 없음(ADR-0007).

SSE 계약:
- `token` : 근거 프로즈 델타
- `recommendation` : `{ products:[{ source_id, name, url, image_url, grounding:[{name,value,provenance}] }] }`
- `clarification` / `done` / `error`

## Acceptance criteria

- [ ] `POST /chat` → 근거 프로즈가 token으로 실시간 스트리밍
- [ ] recommendation 이벤트가 URL·이미지·grounding 포함 카드로 발행
- [ ] 모호 질의 → clarification 이벤트
- [ ] 에이전트/도구 실패 시 error 이벤트, 스트림 종료
- [ ] fake agent 주입 통합 테스트로 이벤트 시퀀스·페이로드 검증(prior art: test_sse_streaming)

## Blocked by
- `01-product-enricher.md`
- `03-recommendation-agent.md`
