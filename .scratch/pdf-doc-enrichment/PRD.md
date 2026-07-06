# PRD: PDF 문서로 상품 임베딩 강화 (적재 시점)

Status: done

## Problem Statement

강화 임베딩(ADR-0015)은 상품명·속성값·LLM 설명으로 검색 인덱스를 만든다. 하지만 실험·연구
장비의 진짜 스펙(재질·규격·용도·물성)은 상품별 **스펙시트/매뉴얼 PDF**에 있고, 이 정보가
설명·임베딩에 안 들어가 있다. 결과적으로 "붕규산 내열 플라스크", "특정 물성" 같은 질의가
스펙에 근거해 상품을 찾지 못한다. 고객사는 상품마다 PDF 링크를 갖고 있는데 이를 검색에
활용할 방법이 없다.

## Solution

고객사가 소스 DB의 상품 행에 **직접-PDF URL 필드**를 채워 두면, 적재 시점에 그 PDF를
읽어 텍스트화하고 LLM 설명 생성의 입력으로 넣는다. LLM이 PDF의 스펙·용도를 한/영으로
증류해 설명에 반영하고, 그 설명이 강화 임베딩에 들어간다. 검색 리콜이 스펙 수준으로
올라가되, **채팅 비용·지연은 불변**이다(지능을 적재 시점으로 앞당김 — C/Route C 원리,
ADR-0015/0016). 기본은 꺼져 있고 `.env` 하나로 켠다.

## User Stories

1. 고객사 운영자로서, 상품 행에 스펙 PDF URL 컬럼을 채워두면 그 스펙이 검색에 반영되길 원한다. 큐레이션한 문서가 검색 품질로 이어지도록.
2. 고객사 운영자로서, PDF 강화를 `.env` 플래그 하나로 켜고 끄고 싶다. 비용이 드는 기능을 통제하려고.
3. 고객사 운영자로서, PDF URL을 담은 컬럼 이름을 내가 정하고 코드는 안 건드리고 싶다. 기존 스키마·명명 관례에 맞추려고.
4. 최종 사용자로서, "붕규산 내열 유리 플라스크"처럼 스펙 기반 질의로 맞는 상품을 찾고 싶다. 상품명만으로는 안 드러나는 특성으로 검색하려고.
5. 고객사 운영자로서, PDF가 없는 상품은 아무 비용·재처리 없이 그대로 두고 싶다. PDF는 일부 상품에만 있으니까.
6. 고객사 운영자로서, 안 바뀐 상품의 PDF를 재적재 때 다시 내려받지 않길 원한다. 대규모 카탈로그에서 불필요한 네트워크·비용을 피하려고.
7. 고객사 운영자로서, PDF를 새 버전으로 교체했을 때 검색이 갱신되게 하는 방법을 문서로 알고 싶다. 스펙 변경이 검색에 반영되도록.
8. 고객사 운영자로서, PDF fetch가 실패하거나(404·타임아웃) PDF가 아닌 응답이 와도 적재가 멈추지 않길 원한다. 한 상품의 문서 문제로 전체 적재가 깨지지 않도록.
9. 고객사 운영자로서, 거대한 PDF가 메모리·시간을 폭주시키지 않도록 크기 상한이 있길 원한다. 저사양 박스에서 안정적으로 돌도록.
10. 고객사 운영자로서, LLM에 들어가는 PDF 텍스트 양(비용)을 글자 상한으로 조절하고 싶다. describe 입력 토큰을 통제하려고.
11. 고객사 운영자로서, 초기 전체 적재·증분 워커·동시 강화 백필 어느 경로로 적재해도 PDF 강화가 동일하게 적용되길 원한다. 운영 경로가 일관되도록.
12. 최종 사용자로서, PDF로 강화됐어도 추천 카드의 이름·가격·속성은 여전히 소스에서 정확히 온다고 신뢰하고 싶다(환각 없음, ADR-0001). PDF는 검색만 돕고 카드 사실을 지어내지 않도록.
13. 개발자로서, PDF 처리(네트워크·파싱)를 실제 네트워크 없이 결정적으로 테스트하고 싶다. CI·로컬에서 안정적으로 검증하려고.
14. 고객사 운영자로서, PDF 강화가 채팅 응답 속도를 늦추지 않길 원한다. 실시간 추천 경험을 유지하려고.

## Implementation Decisions

- **PDF 소스**: 고객사 호스팅 **직접-PDF URL**, **상품 레벨 단일 URL**(변형/field_info 아님).
  컬럼명은 `.env` `PDF_FIELD`로 지정(기본 `it_pdf_url`). 커넥터는 이미 `SELECT *`로 상품 행을
  `doc.raw`에 담으므로 새 컬럼이 자동 노출된다(커넥터 쿼리 무변경). 기존 `field_info.sds_file_url`는
  Sigma MSDS HTML 페이지(직접 PDF 아님)·제3자 대량요청 문제로 채택하지 않는다.
- **`PdfTextExtractor`**(신규 딥모듈): `extract(url) -> str`. 인터페이스 뒤에 fetch·content-type
  가드·크기 상한·파싱·폴백을 은닉. **fetch를 주입**받는다(테스트용). 규칙: 응답이
  `application/pdf`가 아니거나, `PDF_MAX_BYTES` 초과, 타임아웃/예외면 `""`. 파싱은 pypdf,
  CPU 바운드라 스레드로. 추출 텍스트는 공백 정규화 후 앞 `PDF_MAX_CHARS`자(기본 6000)로 트림.
- **설명 주입**: `ProductDescriber.describe(..., pdf_text="")`가 프롬프트에 `문서 발췌:` 블록을
  추가하고, `DESCRIBE_PROMPT`에 "문서 발췌가 있으면 스펙·용도를 설명·키워드에 반영하라"를
  더한다. **PDF 원문은 임베딩 텍스트에 직접 넣지 않는다** — LLM 증류를 거친 설명만 임베딩에
  반영(노이즈·영문 편중 방지, KO/EN 이점 유지).
- **오케스트레이션**: `IngestRunner`가 `doc.raw[PDF_FIELD]`를 읽어 `PdfTextExtractor`로 fetch,
  `describe`에 `pdf_text` 전달. describe는 HTTP를 모른다(관심사 분리). PDF 처리는 `INGEST_PDF`가
  꺼지면 완전히 우회.
- **게이팅(재fetch 회피)**: `ProductDescriber.is_current(source_id, content_hash) -> bool`를 추가해,
  러너가 fetch 전에 "이미 최신 설명이면" fetch를 건너뛴다(설명 캐시를 fetch 게이트로 재사용,
  새 테이블 없음).
- **content_hash에 pdf_url 포함(하위호환)**: `_content_hash`는 `pdf_url`이 **비어있으면 계산이
  기존과 바이트 동일**(PDF 없는 상품 캐시 무효화·재처리 0), **있으면 포함**(URL 변경 → 재처리).
  전체 재-enrich 비용을 피한다.
- **PDF 교체 감지 = URL 변경**: 게이팅은 URL 문자열 기준이라 *같은 URL에 PDF만 교체*는 감지
  못 한다. 고객사는 교체 시 URL에 버전을 넣어(`spec_v2.pdf` 또는 `?v=YYYYMMDD`) 변경을
  흘려보낸다. 이 관례를 README에 명시한다. 바이트해시 감지는 범위 밖.
- **명령 배선**: `ingest_products`·`sync_poll`(워커)·`embed_products` 세 경로 모두 `INGEST_PDF`
  하나로 지배. 켜지면 `PdfTextExtractor`를 러너에 주입.
- **.env**: `INGEST_PDF`(토글) · `PDF_FIELD`(컬럼명) · `PDF_MAX_CHARS`(6000) ·
  `PDF_MAX_BYTES`(10MB) · `PDF_HTTP_TIMEOUT`(10초). 별도 `SYNC_PDF` 없음.
- **의존성**: `pypdf`(순수 파이썬, slim 이미지에 시스템 의존성 없음). `httpx`는 기존 의존성.
- **원칙 유지(ADR-0001)**: PDF는 **검색 리콜만** 강화. 추천 카드의 이름·가격·속성·이미지는 계속
  소스 하이드레이션에서 결정적으로 온다(C, ADR-0016).

## Testing Decisions

- 좋은 테스트는 **외부 행동을 공개 인터페이스로** 검증한다(구현 내부 아님). 리팩터에도 살아남게.
- `PdfTextExtractor`: fetch 주입 + 커밋된 **픽스처 PDF**로 (a) 파싱→알려진 문구 추출, (b) 비-PDF
  content-type → `""`, (c) fetch 예외/타임아웃 → `""`, (d) 크기 초과 → `""`. 네트워크 없음.
- `ProductDescriber`: 페이크 모델로 프롬프트를 캡처해 `pdf_text`가 주입됐는지, `is_current`가
  content_hash 일치/불일치를 옳게 판정하는지. 프리아트: 기존 `test_product_describer.py`.
- `IngestRunner` 배선: `FakePdfExtractor`(정해진 텍스트) 주입 → describe가 `pdf_text`를 받고,
  is_current면 fetch가 스킵되며(호출 카운트), PDF 없으면 content_hash가 기존과 동일함을 검증.
  프리아트: `test_ingest_enrich.py`(RecordingEmbedder)·`test_ingest_runner.py`(카운트 게이팅).
- `_content_hash` 하위호환: pdf_url 없을 때 기존 상품 해시 불변, 있을 때 변함. 프리아트:
  `test_source_connector.py`(content_hash 결정성).

## Out of Scope

- 실제 served PDF로 dev end-to-end(mock·real-source-db엔 `it_pdf_url` 컬럼 없음) — 기능은 기본
  꺼짐이고 픽스처 + FakePdfExtractor 통합테스트로 검증. 실데이터 E2E는 고객사 데이터 연결 시 후속.
- 같은-URL 바이트해시 교체 감지, 변형/field_info 레벨 PDF, OpenAI Batch API의 PDF 특수화.
- PDF 섹션 타겟팅(벤더 포맷 의존), 표 정밀 추출(pdfplumber).
- PDF 원문 보존(별도 저장) — 현재는 설명에 증류만.

## Further Notes

- ADR는 신규로 만들 만큼 되돌리기 어렵거나 놀랍지 않다(기존 ADR-0015 강화 임베딩의 자연스러운
  확장, `.env`로 끌 수 있음). ADR-0015 결과 절에 "적재 시 PDF 문서로 설명 강화(옵션)" 한 줄
  각주면 충분(이슈 03에서 판단).
- 대규모(수십만) PDF 강화는 `embed_products --concurrency`로 병렬화. content-hash·is_current
  게이팅으로 이후엔 변경분만.
