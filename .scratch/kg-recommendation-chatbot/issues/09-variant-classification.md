# 09 — cosmetic vs functional 변형 판별

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

변형 판별을 **추출의 부산물**로 구현(질문 11, CONTEXT: Matching Unit). 옵션 라벨에서 통제 어휘상의 속성이 추출되면 **functional**(그 Variant가 자체 Functional Attribute를 가짐), 추출되지 않으면 **cosmetic**(Product로 합쳐짐). 별도 판별 로직이 아니라 #08 추출의 결과로 갈린다.

## Acceptance criteria

- [ ] PIPET PRO 색상(블루/그레이/오렌지) → cosmetic, Functional Attribute가 Product 레벨에 부착, 추천 시 1개로 합쳐짐
- [ ] 메스플라스크 용량(50ml/500ml…) → functional, 각 Variant가 capacity 속성 보유
- [ ] D₂O 포장(25g/100g…) → functional Variant
- [ ] Matching Unit 규칙대로 속성이 변하는 레벨(Product/Variant)에 부착됨
- [ ] 테스트: cosmetic은 합쳐지고 functional은 개별 매칭 대상이 됨

## Blocked by

- `08-attribute-extractor-text.md`
