# 이슈 01: PdfTextExtractor 딥모듈

Status: done
Type: AFK
Parent: .scratch/pdf-doc-enrichment/PRD.md

## What to build

URL을 받아 PDF 텍스트를 내는 딥모듈 `PdfTextExtractor`. 인터페이스는 `extract(url) -> str`
하나. fetch·content-type 가드·크기 상한·pypdf 파싱·트림·폴백을 이 모듈 뒤에 은닉한다.

- **fetch 주입**: 네트워크를 직접 안 열고 주입받은 async fetch(`url -> (bytes, content_type)`)를
  쓴다. 운영은 httpx 어댑터, 테스트는 페이크. `PDF_HTTP_TIMEOUT`·`PDF_MAX_BYTES`는 어댑터가 적용.
- **content-type 가드**: `application/pdf`가 아니면 `""`.
- **파싱**: pypdf로 전체 페이지 텍스트를 이어붙이고, 공백 정규화 후 앞 `PDF_MAX_CHARS`자로 트림.
  CPU 바운드 파싱은 이벤트 루프를 막지 않게 스레드로.
- **폴백**: fetch 예외·타임아웃·깨진 PDF·크기 초과·빈 텍스트 → `""`(적재를 막지 않는다).

## Acceptance criteria

- [ ] `extract(url)`가 픽스처 PDF(커밋)의 알려진 문구를 담은 텍스트를 반환
- [ ] content-type이 PDF가 아니면 `""`
- [ ] fetch 예외/타임아웃 시 `""`(예외 전파 안 함)
- [ ] 추출 텍스트가 `PDF_MAX_CHARS`로 트림됨
- [ ] fetch 주입으로 네트워크 없이 테스트(테스트 3~4)
- [ ] `pypdf` 의존성 추가(requirements)
- [ ] 전체 스위트 그린

## Blocked by

- None - can start immediately
