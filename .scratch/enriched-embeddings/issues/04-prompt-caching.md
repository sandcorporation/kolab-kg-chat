# 이슈 04: 프롬프트 캐싱 + LLM 비용 관측

Status: done — 실측: 프롬프트 78토큰(OpenAI 캐싱 임계 1024 미달) → cached_tokens=0, 캐싱 무의미. 패딩은 손해. ADR-0015에 결론 기록(실제 레버=Batch API·content-hash). 코드 추가 없음.
Type: AFK
Parent: .scratch/enriched-embeddings/PRD.md

## What to build

LLM 콜의 입력 비용을 프롬프트 캐싱으로 줄이고, 실제 효과를 관측한다. OpenAI **자동 프롬프트 캐싱**은 정적 접두부를 캐시해 캐시된 입력 토큰에 할인을 준다(단 **접두부 ~1024토큰 이상**일 때만 적용). 세 프롬프트(설명 생성·QueryAnalyzer·RagRecommender 생성)를 **캐시 친화적으로 구조화** — 정적 시스템/지시 블록을 **앞에**, 가변 상품·질의·후보를 **뒤에** 둔다.

**비용 관측(이 슬라이스의 핵심)**: LLM 응답의 `usage.prompt_tokens_details.cached_tokens`를 읽어 **캐시 히트 비율·절감**을 측정·로그한다. 이걸로 "우리 프롬프트가 실제로 캐시되는가(현재 ~60토큰이라 1024 미달일 가능성)"를 데이터로 판정하고, 캐싱이 무의미하면 정직히 결론(Batch API 50%·content-hash 게이팅이 진짜 레버)한다. 캐싱이 의미 있으려면 정적 접두부를 키울지(가이드/예시 추가)도 관측 근거로 결정.

## Acceptance criteria

- [ ] 세 프롬프트가 정적 접두부 먼저·가변부 뒤 구조(캐시 친화)
- [ ] LLM 콜에서 `cached_tokens`를 수집해 캐시 히트·절감 관측(로그/집계)
- [ ] 표본으로 실제 캐시 적용 여부 측정(설명 backfill·연속 질의 각각)
- [ ] 결론 기록: 캐싱 효과 유무 + 접두부 확대 가치 판단(정직한 수치)
- [ ] 관측 코드 단위 테스트(cached_tokens 파싱·집계)

## Blocked by

- 이슈 01 (설명 프롬프트 존재 — 질의 프롬프트는 기존 main)
