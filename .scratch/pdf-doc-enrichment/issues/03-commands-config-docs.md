# 이슈 03: 명령 배선 + 설정 + 문서

Status: done
Type: AFK
Parent: .scratch/pdf-doc-enrichment/PRD.md

## What to build

세 적재 경로에서 `INGEST_PDF`가 켜지면 운영 `PdfTextExtractor`(httpx 어댑터)를 러너에 주입하고,
`.env`·README를 갱신한다.

- **명령 배선**: `ingest_products`·`sync_poll`·`embed_products`가 `INGEST_PDF` 켜짐일 때만
  운영 PdfTextExtractor를 만들어 러너에 주입(꺼지면 미주입 → fetch·주입 완전 우회).
- **httpx 어댑터**: `PDF_HTTP_TIMEOUT`·`PDF_MAX_BYTES` 적용하는 운영 fetch(`build_pdf_extractor()`).
- **.env.example**: `INGEST_PDF`·`PDF_FIELD`·`PDF_MAX_CHARS`·`PDF_MAX_BYTES`·`PDF_HTTP_TIMEOUT` 문서화.
- **README**: 적재 절에 PDF 강화 사용법(컬럼 채우기 + `INGEST_PDF=1`)과 **PDF 교체 감지법**
  (교체 시 URL에 버전 부여 `spec_v2.pdf`/`?v=YYYYMMDD` → content_hash로 자동 재처리) 명시.
- **ADR-0015 각주**: "적재 시 PDF 문서로 설명 강화(옵션)" 한 줄(신규 ADR은 과함).

## Acceptance criteria

- [ ] `INGEST_PDF=0`(기본)이면 세 경로 모두 현행과 동일(PDF 무관)
- [ ] `INGEST_PDF=1`이면 러너에 운영 extractor 주입(스모크: 명령이 오류 없이 구성)
- [ ] `.env.example`에 5개 변수 문서화
- [ ] README에 사용법 + PDF 교체 감지법(URL 버전) 명시
- [ ] 전체 스위트 그린

## Blocked by

- 이슈 02 (적재 강화 배선)
