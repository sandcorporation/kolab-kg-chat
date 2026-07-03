# 08 — React 챗: SSE 근거 스트림 + 카드 + 되묻기

Status: done — `frontend/src/App.tsx` + `src/sse.ts`(SSE 파서), 라이브 검증(근거 스트림 + 카드 + kolab URL).

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

React 챗 UI를 완성한다. `POST /chat` SSE를 수제 fetch+ReadableStream 리더로 소비해 이벤트별 렌더:
- `token` → 근거 프로즈 실시간 누적
- `recommendation` → 상품 카드(이름·**URL 링크**·썸네일 이미지·grounding 칩) — Orval 타입 사용
- `clarification` → 되묻기 버블
- `done`/`error` → 종료/오류

## Acceptance criteria

- [ ] 질의 전송 → 근거 프로즈가 토큰 단위로 실시간 표시
- [ ] recommendation → 카드 렌더(상품명·클릭 가능한 kolab 링크·썸네일·grounding)
- [ ] clarification → 되묻기 UI
- [ ] error → 오류 표시, 스트림 안전 종료
- [ ] 핵심 컴포넌트 vitest 렌더 테스트(이벤트→렌더)

## Blocked by
- `04-sse-agent-rewire.md`
- `06-react-scaffold-nginx.md`
- `07-orval-client.md`
