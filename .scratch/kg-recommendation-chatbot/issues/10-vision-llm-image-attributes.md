# 10 — 비전 LLM + ImageTriage

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

이미지 속 스펙을 **비전 LLM 직독**으로 추출(ADR-0005, 고전 OCR 아님). **ImageTriage**가 스펙/표/도면 이미지만 선별해 비전 호출 비용을 통제하고, 통과 이미지에서 유형별 통제 어휘로 속성 추출 후 `source=llm_ocr`로 태깅(ADR-0004). 점도계 VISCO B(스펙이 이미지에만 있음)로 검증. 테스트는 비전 더블.

## Acceptance criteria

- [ ] ImageTriage가 마케팅 사진과 스펙 이미지를 구분(스펙만 통과)
- [ ] 점도계의 스펙 이미지에서 측정범위·정밀도 등 속성 추출
- [ ] 이미지 유래 속성은 `source=llm_ocr` + confidence로 태깅
- [ ] 텍스트에서 이미 확정된 속성은 비전 호출 생략(비용 절감)
- [ ] 가짜 비전 더블로 고정 이미지 → 기대 속성 검증

## Blocked by

- `08-attribute-extractor-text.md`
