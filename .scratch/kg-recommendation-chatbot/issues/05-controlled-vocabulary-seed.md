# 05 — 유형별 통제 어휘 시드 정의

Status: ready-for-human

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

Functional Attribute의 **유형별 통제 어휘(초기 속성 스키마)** 를 정의한다(ADR-0001). 통제 어휘는 평평하지 않고 Product Type마다 다르다(CONTEXT: Product Type/Functional Attribute). 사람(아키텍트/도메인)이 초기 스키마를 정해야 하므로 HITL.

출발점 유형과 결정적 차원(예):
- **유리/소모품**: 재질, 온도범위(min/max), 내화학성, 멸균등급, 용량
- **전동/계측 기기**: 측정범위, 정밀도, 전원, 인터페이스, 호환부속
- **시약/화공약품**: 순도, CAS, 농도, 위험/보관, 포장 단위

각 차원의 정규형(숫자+단위 / 열거형)을 명시하고, "후보 적재→사람 승격" 성장 루프의 골격을 정한다.

## Acceptance criteria

- [ ] 시드 4종이 속한 유형들의 속성 스키마가 정의됨(정규형 포함)
- [ ] 각 차원이 숫자범위형/열거형/불리언 중 무엇인지 명시
- [ ] 어휘에 없는 차원을 만났을 때의 "후보" 처리 규칙 정의
- [ ] (선택) 차광=light_protection 같은 함정 차원 포함 여부 결정
- [ ] 산출물이 #08 AttributeExtractor가 소비할 형태로 문서화/구성됨

## Blocked by

None - can start immediately
