# 16 — Retriever(속성 필터) + RecommendationComposer

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

읽기 경로의 첫 end-to-end 답. **Retriever**가 요구조건(#15)을 GraphStore의 **속성 필터(SQL)** 로 매칭해 후보 Product/Variant를 뽑고, **RecommendationComposer**가 각 후보를 **충족한 Functional Attribute(+provenance)** 와 짝지어 **근거 인용된 Recommendation**을 JSON으로 반환한다(ADR-0001, CONTEXT: Recommendation). Django Ninja 엔드포인트(비스트리밍).

## Acceptance criteria

- [ ] Condition(temp ≤ -150℃ 등) 질의 → 속성 충족 Product/Variant 반환
- [ ] 다중 Condition AND 매칭
- [ ] 각 추천에 "충족 요구조건 ← 속성(provenance 포함)" 근거 동봉
- [ ] 기능 변형은 개별 매칭, 외형 변형은 Product로 합쳐짐(#09 규칙)
- [ ] `POST /api/recommend`(또는 유사) → 근거 포함 JSON Recommendation
- [ ] 가짜 LLM + 시드 그래프로 결정적 통합 테스트

## Blocked by

- `08-attribute-extractor-text.md`
- `15-requirement-parser.md`
