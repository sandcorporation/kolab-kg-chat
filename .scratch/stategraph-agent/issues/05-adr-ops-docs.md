# 이슈 05: ADR + 운영/문서

Status: done — ADR-0013(StateGraph·무상태 메모리·토큰 트림), .env.example(AGENT_TOKEN_BUDGET·AGENT_HISTORY_TURNS), README step2(가격·멀티턴·트림).
Type: AFK
Parent: .scratch/stategraph-agent/PRD.md

## What to build

되돌리기 비용이 있는 결정들을 **짧은 ADR 1건**으로 남긴다: (a) prebuilt `create_react_agent` → 커스텀 StateGraph, (b) 무상태 클라이언트-히스토리 메모리 모델, (c) 토큰 예산 트리밍. ADR-0007/0011과의 관계(단일 읽기 경로 내부 구현 교체)를 명시. `.env.example`에 `AGENT_TOKEN_BUDGET`·`AGENT_HISTORY_TURNS` 문서화, README에 멀티턴·가격·컨텍스트 방어 반영, CONTEXT.md 용어(필요 시) 갱신.

## Acceptance criteria

- [ ] ADR 신규 1건(StateGraph·무상태 메모리·토큰 트리밍 결정과 근거·대안)
- [ ] `.env.example`에 AGENT_TOKEN_BUDGET·AGENT_HISTORY_TURNS 추가
- [ ] README에 멀티턴 대화·가격 표시·컨텍스트 방어 반영
- [ ] 전체 백엔드 스위트 그린

## Blocked by

- 이슈 01–04
