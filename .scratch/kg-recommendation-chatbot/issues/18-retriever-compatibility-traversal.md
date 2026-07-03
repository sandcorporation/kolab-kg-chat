# 18 — Retriever 호환 순회 (AGE 다홉)

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

Retriever에 **AGE 다홉 순회**(질문 9-B)를 추가. "내가 쓰는 X와 호환되는/부속/소모품" 같은 **명시적 엣지 체인**(Compatibility)을 openCypher로 따라간다(ADR-0003). 가변 깊이 의존 체인("X를 쓰려면 결국 무엇이 필요한가")을 펼친다.

## Acceptance criteria

- [ ] "X와 호환되는 상품" → Compatibility 엣지 1~N홉 순회 결과 반환
- [ ] 가변 깊이 의존 체인 펼침(예: 장비→부속→소모품)
- [ ] 호환 근거(엣지 경로)가 추천에 동봉됨
- [ ] 통합 테스트: 시드 그래프의 호환 관계로 기대 경로 반환

## Blocked by

- `16-retriever-attribute-filter-composer.md`
