# 이슈 01: DescriptionGenerator + 캐시 + content-hash 게이팅

Status: done — ProductDescriber(한/영 설명 LLM) + DescriptionStore(캐시) + content-hash 게이팅·실패 폴백. 테스트 3.
Type: AFK
Parent: .scratch/enriched-embeddings/PRD.md

## What to build

상품을 받아 **한/영 설명 + 검색 키워드**를 생성하는 딥모듈과, 그걸 content-hash로 게이팅·캐시하는 저장소. `describe(name, attributes) → 설명` (LLM, `RAG_DESCRIPTION_MODEL` 기본 gpt-4o-mini). 생성한 설명을 `source_id → (content_hash, 설명)`로 저장하고, 상품의 이름·속성이 안 바뀌면(같은 content_hash) **재호출하지 않는다**(캐시 히트). 프롬프트는 캐시 친화적으로 정적 지시 먼저·가변 상품정보 뒤. 실패(오류·타임아웃)는 빈 설명으로 폴백(적재 차단 금지). 실측 참고: 상품당 입력~105·출력~82 토큰.

## Acceptance criteria

- [ ] `describe(name, attributes)`가 상품명·속성을 프롬프트에 담아 LLM 호출, 설명 반환
- [ ] DescriptionStore가 설명을 content_hash와 함께 저장, 조회 제공
- [ ] content-hash 게이팅: 같은 상품 재요청 시 LLM **재호출 없음**(counting double), 변경 시 재생성
- [ ] 생성 실패 시 빈/폴백 반환(예외 전파 안 함)
- [ ] fake LLM으로 결정적 단위 테스트(프롬프트 구성·게이팅·폴백)

## Blocked by

None - can start immediately
