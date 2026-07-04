# 이슈 02: RagRecommender (retrieve-then-read) — 트레이서

Status: done — RagRecommender(질의이해→검색→LLM 선택·근거, 선택줄 파싱·suppress, 검색 중 status, 현재 질의만). 라이브: 추천 6·앵커링 해소.
Type: AFK
Parent: .scratch/rag-recommender/PRD.md

## What to build

RAG 읽기 컴포넌트. 기존 `astream(query, history)`/`run(...)` 인터페이스를 그대로 노출한다. HybridRetriever로 후보를 얻어 **후보(번호·이름·속성) + 히스토리(참조용) + 질의**를 짧은 프롬프트로 만들고 **단일 스트리밍 LLM 호출**을 한다. LLM은 첫 줄에 `선택: 2, 5`(없으면 `선택: 없음`)를 쓰고 다음 줄부터 근거를 쓴다.

**선택 파싱(결정적)**: 래퍼가 첫 선택 줄을 파싱해 후보 번호→source_id로 매핑(추천 id 포착)하고, 그 줄은 토큰 스트림에서 suppress, 이후 근거만 token 이벤트로 흘린다. 검색 시작 시 `검색 중…` status 1회. `선택: 없음`이면 recommended 비고 되묻기만. ContextTrimmer로 프롬프트를 토큰 예산 내로. 도구 호출·재검색 없음.

이 단계에선 아직 기본 읽기 경로로 배선하지 않는다(A/B 후 컷오버는 이슈 04).

## Acceptance criteria

- [ ] astream이 `검색 중…` status → 근거 token → recommendation → done 방출
- [ ] 첫 줄 `선택:`이 토큰 스트림에서 suppress되고 근거만 흐름
- [ ] 선택 파서: `선택: 2, 5`→source_id 매핑, `선택: 없음`→빈 추천, 형식 이탈→빈 추천(안전)
- [ ] 검색은 현재 질의로만(히스토리 바뀌어도 retriever 입력 동일), 히스토리는 프롬프트에 참조용 포함
- [ ] 도구 호출 없음, 프롬프트는 2~3줄 지침
- [ ] ScriptedChatModel + fake retriever로 결정적 테스트 + 실 모델 라이브 스모크

## Blocked by

- 이슈 01 (HybridRetriever)
