# 24 — OpenAI 동시성 리미터 + 백오프 + 큐잉

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

100 동시 챗의 **진짜 천장**인 OpenAI 레이트 리밋 대응(ADR-0007). 채팅/임베딩/비전 호출에 **동시성 세마포어**로 상한을 두고, 초과분은 큐잉, 429에 **지수 백오프** 재시도. 비전 호출(쓰기 경로)과 챗 호출(읽기 경로)의 레이트 버짓을 분리.

## Acceptance criteria

- [ ] 동시 LLM 호출이 설정된 상한을 넘지 않음(세마포어)
- [ ] 초과 요청은 큐잉되어 순차 처리
- [ ] 429/레이트 오류에 지수 백오프 재시도
- [ ] 비전(쓰기)과 챗(읽기) 호출 버짓 분리
- [ ] 테스트: 상한 초과 부하에서 호출이 직렬화/재시도됨(가짜 제공자)

## Blocked by

- `19-sse-streaming.md`
