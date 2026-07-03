# 04 — 비전 수집 트레이서 (이미지 → 속성 → 그래프)

Status: ready-for-agent

## Parent

`.scratch/vision-spec-extraction/PRD.md`

## What to build

진짜 end-to-end 트레이서. `ImageAttributeExtractor(OpenAIVisionClient)`를 수집 경로(`SyncOrchestrator.process_product`, 이미 image_extractor 호출)에 주입한다. 이미지에서 추출된 Functional Attribute가 `provenance=llm_ocr`(ADR-0004)로 그래프에 병합되며, 텍스트에서 이미 확정된 차원은 `known_names`로 비전에서 생략(이슈 10). 이미지 fetch/파싱 실패는 해당 상품만 건너뛰고 수집을 지속한다. content-hash 게이팅(ADR-0008)을 그대로 상속.

## Acceptance criteria

- [ ] process_product가 (텍스트 + 이미지) 속성을 병합해 그래프에 저장
- [ ] 이미지 유래 속성은 `provenance=llm_ocr`로 태깅
- [ ] 텍스트에서 확정된 속성명은 비전 호출에서 제외(known_names)
- [ ] 비전 실패 시 그 상품만 스킵, 나머지 수집 지속
- [ ] FakeVisionClient 주입 통합 테스트로 이미지 속성이 그래프에 병합됨을 검증(test_full_load 확장)

## Blocked by

- `01-connector-explan-images.md`
- `02-openai-vision-client.md`
- `03-image-triage-redesign.md`
