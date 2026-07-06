# 이슈 03: ADR-0017 + 문서 + 품질 비교

Status: done
Type: AFK
Parent: .scratch/iterative-retrieval/PRD.md

## What to build

되돌리기 어려운 트레이드오프(비용↑ ↔ 검색 품질↑)를 ADR로 남기고, 설정을 문서화하고,
현행 단일 패스와 반복 루프의 품질을 비교한다.

- **ADR-0017**: ADR-0015(비용 위해 QueryAnalyzer 제거)를 되돌림. 결정(질의생성 복구 + 만족까지
  N회 반복 + 팔로업 라우팅), 이유(첫 시도 실패 시 재검색), 비용(채팅당 1→2~6), 대안(별도 판정
  LLM·점수 임계 기각), 판정=선택 재사용, prod=새 기본값·재배포 안 함으로 보호.
- **.env.example**: `AGENT_MAX_ITERS`(기본 3, 1이면 사실상 단일 패스로 완화) 문서화.
- **품질 비교**: 대표 질의 세트로 현행(단일 패스) vs 반복 루프를 A/B — 성공률(맞는 유형 추천),
  재시도가 실제로 살려낸 질의 예시, 채팅당 콜 수 관측.

## Acceptance criteria

- [ ] ADR-0017 신규(0015 되돌림·비용·대안·판정 재사용)
- [ ] .env.example에 AGENT_MAX_ITERS
- [ ] 현행 vs 반복 품질 비교 결과 기록(성공률·살려낸 질의·콜 수)
- [ ] 전체 스위트 그린

## Blocked by

- 이슈 02 (반복 루프)
