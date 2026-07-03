# SSE 구조화 타입 이벤트 + 턴 단위 인라인 스트리밍 (Redis 불필요)

실시간 토큰 스트리밍(플랜 5번)과 구조화된 근거 추천(ADR-0001)을 ~100개 동시 챗에 동시에 제공해야 한다.

## 결정

**SSE 프로토콜** — 한 스트림에 named 이벤트 + JSON 페이로드를 흘린다(`event: {type}\ndata: {json}\n\n`). 토큰 스트리밍과 구조화는 양자택일이 아니다(embed-chat `sse.py`에서 검증됨). 이벤트 타입: `token`(프로즈 델타), `recommendation`(상품+인용 속성+provenance), `clarification`(되묻기, 질문 14), `done`, `error`.

**연결 모델 (A) 턴 단위 스트리밍 POST** — 질의 요청이 그 같은 연결로 답을 스트리밍한다. langgraph 에이전트는 그 async 요청 핸들러 **안에서 인라인** 실행되며 `astream_events()` + custom `StreamWriter`로 이벤트를 흘린다. 지속 SSE(GET)+별도 POST 모델은 쓰지 않는다.

**Redis pub/sub 미사용** — 에이전트가 SSE 연결과 같은 인스턴스에서 인라인 실행되므로 인스턴스 간 라우팅이 없다. kolabshop은 단일 테넌트·HITL 없음이라 embed-chat이 Redis를 쓴 이유(워커 분리·HITL 주입·멀티인스턴스 fan-out)가 없다.

## 100-동시 처방

챗은 I/O 바운드(OpenAI·DB 대기)라 async가 본질적 해법이다. 진짜 제약과 대비:
- **OpenAI 레이트 리밋(진짜 천장)** — 동시성 세마포어로 제한 + 큐잉, 429 지수 백오프. 비전 호출(ADR-0005)은 챗과 레이트 버짓 분리.
- **이벤트 루프 비차단** — 전 구간 async(ADR-0006의 규율).
- **Postgres 커넥션 풀링**(asyncpg/pgbouncer, ~20–50).
- **복원력**: uvicorn 2+ 레플리카 behind LB. 모델 (A)라 다중 인스턴스여도 Redis 불필요.
- **쓰기 경로 분리**: 수집/추출(CDC→비전LLM)은 별도 워커로 떼어 챗 지연과 경쟁시키지 않는다.

## 결과

- Orval은 이벤트 페이로드 타입 + 비스트리밍 REST를 생성하고, SSE 스트림 소비만 얇은 수제 리더로(플랜 6번).
- 추후 HITL·지속 연결이 요구되면 embed-chat의 Redis pub/sub 패턴으로 승격한다(검증된 fallback).
