# 이슈 02: 적재 강화 배선 (describe 주입 + 게이팅 + 러너)

Status: done
Type: AFK
Parent: .scratch/pdf-doc-enrichment/PRD.md

## What to build

PDF 텍스트를 설명 생성에 주입하고, 러너가 상품별 PDF URL을 읽어 오케스트레이션하며,
재fetch·재처리를 게이팅한다. 실제 임베딩 텍스트는 LLM이 증류한 설명을 통해서만 PDF를 반영한다.

- **describe 주입**: `ProductDescriber.describe(..., pdf_text="")`가 프롬프트에 `문서 발췌:`
  블록을 더하고, `DESCRIBE_PROMPT`에 "문서 발췌가 있으면 스펙·용도를 설명·키워드에 반영"을 추가.
  PDF 원문은 임베딩 텍스트에 직접 넣지 않는다(증류만).
- **is_current 게이트**: `ProductDescriber.is_current(source_id, content_hash) -> bool` 추가.
  러너가 fetch 전에 "이미 최신 설명"이면 fetch를 건너뛴다(설명 캐시를 fetch 게이트로 재사용).
- **content_hash 하위호환**: `_content_hash`에 `pdf_url`을 포함하되 **비어있으면 기존과 바이트
  동일**(PDF 없는 상품 재처리 0), 있으면 포함(URL 변경 → 재처리).
- **러너 오케스트레이션**: `IngestRunner`가 (선택적으로 주입된) PdfTextExtractor로
  `doc.raw[PDF_FIELD]`를 fetch해 `describe(..., pdf_text)`에 넘긴다. extractor 미주입이면 현행 그대로.

## Acceptance criteria

- [ ] describe가 pdf_text를 받으면 프롬프트(문서 발췌)에 포함 — 페이크 모델로 검증
- [ ] 러너가 PDF URL을 읽어 FakePdfExtractor 텍스트를 describe로 전달(RecordingDescriber로 캡처)
- [ ] is_current면 러너가 fetch를 스킵(extractor 호출 카운트 0)
- [ ] pdf_url 빈 상품의 content_hash는 기존과 동일; pdf_url 있으면 달라짐
- [ ] extractor 미주입 시 현행 적재 동작 불변(회귀 없음)
- [ ] 전체 스위트 그린

## Blocked by

- 이슈 01 (PdfTextExtractor)
