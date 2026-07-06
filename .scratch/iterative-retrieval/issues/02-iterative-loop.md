# 이슈 02: RagRecommender 반복 루프 + 팔로업 + 스트리밍

Status: done
Type: AFK
Parent: .scratch/iterative-retrieval/PRD.md

## What to build

RagRecommender를 단일 패스에서 **에이전틱 반복 검색**으로 바꾼다. analyze로 라우팅하고,
만족할 때까지 최대 N회 재검색하며, 팔로업은 검색을 건너뛴다.

- **라우팅**: `analyze(query, history)` → FOLLOWUP이면 히스토리로 답변 스트리밍 + `result([])`.
- **반복 루프**(새 검색): `for i in range(AGENT_MAX_ITERS)`:
  - status 이벤트(i==0 "검색 중…", 이후 "다른 검색어로 다시 찾는 중… i/N")
  - `retrieve(keywords, semantic)` (교체)
  - 선택 스트림 → **첫 줄 '선택:' 엿보기**: 만족(유효 선택)→나머지 근거 토큰 스트리밍+result(ids);
    불만족&마지막→정직한 폴백+result([]); 불만족&잔여→스트림 중단+reformulate+재시도
  - **무진전 가드**: 재검색어가 직전과 동일하면 조기 종료(폴백)
- **판정 = 선택 재사용**: `parse_selection`이 유효 번호면 만족. 별도 판정 LLM 없음.
- **런타임 배선**: `build_default_context`가 QueryAnalyzer를 만들어 주입. `AGENT_MAX_ITERS`(기본 3).

## Acceptance criteria

- [ ] 1회차 만족 → 재시도 없음(analyze1·select1), 근거 토큰 스트리밍 + result(ids)
- [ ] 1회차 `선택: 없음` → reformulate(거부후보 반영) → 2회차 만족
- [ ] N 소진까지 불만족 → 정직한 폴백 + result([])
- [ ] 무진전(재검색어 동일) → 조기 종료
- [ ] 팔로업 → 검색·루프 스킵, 히스토리로 텍스트 답변 + result([])
- [ ] 재시도마다 status 이벤트, 최종 근거만 token 스트리밍
- [ ] runtime이 analyzer 주입, AGENT_MAX_ITERS 반영
- [ ] 전체 스위트 그린

## Blocked by

- 이슈 01 (QueryAnalyzer)
