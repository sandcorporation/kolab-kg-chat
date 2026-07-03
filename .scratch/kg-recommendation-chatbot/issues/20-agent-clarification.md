# 20 — 에이전트 분기: 명확화 되묻기 (1회)

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

혼합 에이전트의 제한된 에이전트성(질문 14). 질의가 모호하면 **딱 1회** `clarification` 이벤트로 되묻고, 답을 받아 요구조건을 보강해 진행한다. 과한 되묻기 방지(1회 제한), 어지간하면 가정을 명시하고 진행.

## Acceptance criteria

- [ ] 모호 질의 → `clarification` 이벤트 1회 발행
- [ ] 사용자 응답으로 요구조건 보강 후 검색 진행
- [ ] 되묻기는 최대 1회(루프 방지)
- [ ] 명확하면 되묻지 않고 바로 추천
- [ ] 통합 테스트: 모호/명확 두 경로 검증

## Blocked by

- `19-sse-streaming.md`
