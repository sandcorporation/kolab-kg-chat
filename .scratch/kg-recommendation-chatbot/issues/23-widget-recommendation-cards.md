# 23 — Widget Recommendation 카드 + 근거 렌더

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

위젯이 `recommendation` 구조화 이벤트를 받아 **상품 카드 + 근거**(충족 요구조건 ← Functional Attribute, provenance 포함)를 렌더한다. `clarification` 이벤트는 되묻기 UI로 표시한다. 토큰 프로즈와 구조화 카드가 한 대화에 공존한다.

## Acceptance criteria

- [ ] `recommendation` 이벤트 → 상품 카드(이름·가격·근거 속성) 렌더
- [ ] 근거에 provenance(확정/추측/이미지) 표시
- [ ] `clarification` 이벤트 → 되묻기 입력 UI
- [ ] 토큰 프로즈 + 카드 + 되묻기가 한 스트림에서 자연스럽게 섞임
- [ ] 컴포넌트 테스트로 각 이벤트 타입 렌더 검증

## Blocked by

- `22-widget-skeleton-orval.md`
