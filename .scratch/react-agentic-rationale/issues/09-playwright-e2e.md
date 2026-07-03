# 09 — Playwright E2E (React 단일 엔드포인트)

Status: done — `frontend/e2e/chat.spec.ts` + `playwright.config.ts`, MCP 브라우저로 전체 스택 E2E 라이브 검증(AGENT_FAKE=1).

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

nginx 단일 엔드포인트(`http://localhost/`)의 React 앱을 실브라우저(Playwright)로 E2E 검증한다. 질의 입력 → 근거 프로즈 스트리밍 → 추천 카드(URL 링크·이미지·grounding) → 되묻기 시나리오까지. 백엔드는 실 그래프(시드) + 실/모의 LLM.

## Acceptance criteria

- [ ] 앱 로드(제목·입력·전송)
- [ ] 질의 → 근거 프로즈가 스트리밍으로 나타남
- [ ] 추천 카드에 상품명·클릭 가능한 kolab URL·grounding 표시
- [ ] 모호 질의 → 되묻기 표시
- [ ] 스크린샷 저장(시각 확인)

## Blocked by
- `08-react-chat.md`
