# 이슈 04: (조건부) RAG 컷오버 + 에이전트/도구 제거 + ADR

Status: done — build_default_context→RagRecommender 컷오버, 에이전트·GraphTools·eval·도구프롬프트 제거, ADR-0014(0007/0011/0013 대체), RAG_TOP_K. 126 passed.
Type: HITL
Parent: .scratch/rag-recommender/PRD.md

## What to build

**이슈 03 A/B에서 RAG ≥ 에이전트일 때만** 진행. RAG를 단일 읽기 경로로 확정한다: `build_default_context`가 RagRecommender를 조립하고, 프론트 상태줄은 `검색 중…` 하나로 동작. tool-calling 잔재 제거 — langgraph StateGraph, GraphTools 도구 래퍼(find_products·find_compatible·get_attributes·search_products·semantic_search·recommend as tools)·`Command`/`ToolNode`·`TOOL_STATUS_LABELS`·7섹션 도구 프롬프트. (GraphStore 조회 메서드·SemanticSearch·엔리처는 유지.) ADR-0007/0011/0013을 대체하는 새 ADR을 A/B 근거와 함께 남긴다. A/B가 미달이면 이 이슈는 보류하고 사유를 기록한다.

## Acceptance criteria

- [ ] (조건: RAG≥에이전트) runtime이 RagRecommender를 읽기 경로로 배선
- [ ] StateGraph·도구 래퍼·TOOL_STATUS_LABELS·도구 프롬프트 제거, 관련 테스트 정리
- [ ] 프론트 상태줄 `검색 중…` 동작(status 라벨 1개), SSE 계약 불변
- [ ] 새 ADR(ADR-0007/0011/0013 대체, A/B 결과 근거)
- [ ] 전체 스위트 그린 + Playwright 라이브(diagnose 시나리오 재검색 없음, 서술형·키워드·가격·멀티턴, 첫 토큰 단축)

## Blocked by

- 이슈 03 (A/B 결과)
