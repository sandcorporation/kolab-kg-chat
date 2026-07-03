# 이슈 02: 컨텍스트 길이 방어 (토큰 예산 트리밍)

Status: ready-for-agent
Type: AFK
Parent: .scratch/stategraph-agent/PRD.md

## What to build

`agent` 노드가 매 모델 호출 직전 메시지를 **토큰 예산으로 트림**한다. 시스템 프롬프트는 항상 유지(`include_system`), 최근 메시지 우선. 이로써 멀티턴 누적과 턴 내 도구출력 누적을 모두 방어한다. 트리밍은 카운터 주입이 가능한 딥모듈(**ContextTrimmer**)로 분리해 결정적으로 테스트한다. 예산은 `.env`(`AGENT_TOKEN_BUDGET`)로 제어하고, 운영은 모델 토크나이저·테스트는 결정적 카운터를 쓴다. 기존 `recursion_limit`은 유지.

## Acceptance criteria

- [ ] ContextTrimmer가 예산 초과 시 시스템 프롬프트 유지 + 오래된 메시지부터 제거, 예산 내면 그대로
- [ ] agent 노드가 매 모델 호출 직전 트림 적용
- [ ] `AGENT_TOKEN_BUDGET` env로 예산 제어(기본값 보수적)
- [ ] 결정적 카운터 주입으로 경계 동작 단위 테스트
- [ ] 트리밍이 있어도 도구 루프·최종 rationale 정상(회귀 없음)

## Blocked by

- 이슈 01 (StateGraph agent 노드)
