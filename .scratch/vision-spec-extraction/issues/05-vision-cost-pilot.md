# 05 — 비전 비용 파일럿 + 예측

Status: ready-for-human

## Parent

`.scratch/vision-spec-extraction/PRD.md`

## What to build

스펙 이미지가 있는 실제 상품 약 100건에 **실제 gpt-4o vision**을 실행해 이미지당 토큰·비용을 실측하고, 전체 카탈로그 비전 추출 비용을 예측한다(텍스트 B와 동일 방식). 실제 OpenAI 비용이 발생하므로 사람이 지출을 승인·트리거한다(HITL).

## Acceptance criteria

- [ ] 실 vision으로 100건(스펙 이미지 보유) 처리, 이미지당 평균 토큰·비용 측정
- [ ] 트리아지 적용 시 상품당 비전 호출 수가 상한 내로 통제됨 확인
- [ ] 전체(스펙 이미지 보유 상품 수 기준) 비전 비용 예측치 산출
- [ ] 추출된 이미지 속성이 그래프에 반영되고 챗 추천에서 근거(llm_ocr)로 인용됨 확인

## Blocked by

- `04-vision-ingestion-tracer.md`
- 실제 OpenAI 비용 지출 승인
