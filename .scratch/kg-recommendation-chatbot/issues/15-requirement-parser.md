# 15 — RequirementParser

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

자연어 질의를 **구조화 요구조건**으로 변환하는 LLM 모듈(지식소스 C, ADR-0001). 질의에서 Application·Condition·이미 쓰는 Product를 뽑아, 매칭 가능한 요구조건 집합으로 만든다. 근거 인용을 위해 **요구조건을 명시적으로 출력**한다(나중에 인용 가능). 테스트는 가짜 LLM.

## Acceptance criteria

- [ ] "초저온(-150℃ 이하) 세포 보관용 바이알" → {Application: 세포 보관, Condition: temp ≤ -150℃ 등} 구조 출력
- [ ] "ATAGO 점도계와 호환되는 표준액" → 호환 대상 Product 식별
- [ ] 요구조건이 명시적·인용 가능한 형태로 출력됨
- [ ] 가짜 LLM으로 결정적 테스트(외부 행동만)

## Blocked by

- `02-postgres-age-pgvector.md`
