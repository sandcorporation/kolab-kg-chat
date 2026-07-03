# 21 — 에이전트 분기: 0건 제약 완화 (1회)

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

검색 결과가 0건이면 에이전트가 **제약을 1회 완화**해 재검색한다(질문 14). 완화한 내용을 사용자에게 명시("정확히 맞는 건 없어 ~를 완화해 찾았습니다").

## Acceptance criteria

- [ ] 0건 → 제약 1회 완화 후 재검색
- [ ] 완화 내용이 답변/근거에 명시됨
- [ ] 완화는 최대 1회(무한 완화 방지)
- [ ] 완화 후에도 0건이면 정직하게 "없음" 응답
- [ ] 통합 테스트: 0건→완화→후보 경로 검증

## Blocked by

- `19-sse-streaming.md`
