# 02 — Agent Tools (그래프 도구)

Status: done — `apps/agent/tools.py` (GraphTools), 테스트 `tests/test_agent_tools.py` 통과.

## Parent
`.scratch/react-agentic-rationale/PRD.md`

## What to build

langgraph 에이전트가 호출할 그래프 도구들을 GraphStore 위 얇은 래퍼로 구현한다:
- `find_products(conditions)` — 속성 필터 검색 → 상품 목록
- `find_compatible(product_id, depth)` — AGE 다홉 호환 순회
- `get_attributes(product_id)` — 특정 상품 속성(근거 상세)
- `recommend(ids)` — 에이전트의 최종 선택을 기록(다운스트림이 이 id들로 카드 구성)

도구는 결정적이며 그래프만 건드린다.

## Acceptance criteria

- [ ] 각 도구가 정의된 시그니처로 그래프 결과를 반환
- [ ] find_products가 조건(AND) 매칭 상품 반환
- [ ] find_compatible가 1~depth 홉 도달 상품 반환
- [ ] recommend(ids)가 최종 선택 집합을 표현
- [ ] 실제 AGE 컨테이너 대상 통합 테스트(prior art: test_graph_store/test_compatibility)

## Blocked by
None - can start immediately
