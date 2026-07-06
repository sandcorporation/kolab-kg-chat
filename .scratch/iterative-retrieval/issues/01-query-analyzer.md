# 이슈 01: QueryAnalyzer 복구·확장 + retriever 적응

Status: done
Type: AFK
Parent: .scratch/iterative-retrieval/PRD.md

## What to build

제거됐던 질의생성 LLM(QueryAnalyzer)을 되살리고, 반복 루프가 쓸 두 능력과 팔로업 라우팅을
더한다. HybridRetriever가 분석된 검색어를 받도록 시그니처를 되돌린다.

- `analyze(query, history)` → 라우팅 + 초기 검색어. LLM이 **FOLLOWUP**(히스토리 있고 명백히 이전
  상품 참조 시만; 첫 턴·애매하면 새 검색 — 보수적)인지, 아니면 **한/영 키워드 + 시맨틱 질의**인지
  JSON으로 출력. 파싱 실패는 원 질의로 폴백.
- `reformulate(query, prev_terms, rejected_names)` → 원 질의 + 직전 검색어 + 거부된 후보 이름을
  보고 **직전과 다른** 한/영 키워드 + 시맨틱 질의를 생성.
- `HybridRetriever.retrieve(keywords, semantic_query)` → 키워드마다 keyword_search + 시맨틱 1회 →
  합집합·중복제거·top-K + 설명 부착(C 유지).

## Acceptance criteria

- [ ] analyze: 새 검색 질의 → 키워드/시맨틱 파싱; 명백한 팔로업(+히스토리) → FOLLOWUP
- [ ] analyze: 히스토리 없으면(첫 턴) 항상 새 검색
- [ ] analyze: JSON 파싱 실패 → 원 질의로 폴백(검색 계속)
- [ ] reformulate: 거부 후보를 반영해 직전과 다른 검색어 산출
- [ ] retrieve(keywords, semantic): 키워드 합집합 ∪ 시맨틱, 중복제거·설명 부착
- [ ] ScriptedChatModel로 네트워크 없이 테스트(4~6건)
- [ ] 전체 스위트 그린

## Blocked by

- None - can start immediately
