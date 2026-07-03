# 이슈 04: 멀티턴 메모리 (무상태 클라이언트 히스토리)

Status: ready-for-agent
Type: AFK
Parent: .scratch/stategraph-agent/PRD.md

## What to build

무상태 멀티턴 메모리. 요청 스키마 `ChatIn`에 `history: list[{role, content}]`(선택, 기본 빈 배열)를 더하고, `prepare` 노드가 이를 Human/AI 메시지로 변환해 현재 질의 앞에 병합한다. 프론트는 표시용 `turns`에서 최근 N턴을 **직렬화(HistorySerializer)** 해 보내되, 봇 턴은 **라시오날레 텍스트 + 추천 상품 요약 한 줄(상품명 + 가격 범위)** 로 압축한다. 히스토리 턴 수는 `.env`(`AGENT_HISTORY_TURNS`)로 상한. views가 history를 에이전트에 전달.

## Acceptance criteria

- [ ] `ChatIn.history` 추가(하위호환), views가 astream에 history 전달
- [ ] prepare 노드가 history→메시지 병합, 모델이 이전 맥락을 봄(스크립트 모델이 받은 messages 검증)
- [ ] history 없으면 단일턴 회귀 없음
- [ ] 프론트가 turns를 history로 직렬화(봇 턴=라시오날레+추천 상품명·가격범위)해 전송, 최근 N턴 상한
- [ ] Playwright 멀티턴 라이브: 추천 → "첫 번째 상품 스펙" 후속 이해

## Blocked by

- 이슈 01 (StateGraph prepare 노드)
- 이슈 03 (히스토리 요약에 가격 포함)
