# PRD — 이미지 스펙 추출 (Vision) : it_img·it_explan에서 Functional Attribute 뽑기

Status: ready-for-agent

## Problem Statement

실제 kolabshop 데이터에서 상품 스펙(재질·온도·용량·측정범위 등 Functional Attribute)은 **텍스트가 아니라 이미지에 있다.** 실측: 활성 610,609건 중 `it_img1` 보유 **610,582건(99.99%)**, `it_explan`에 `<img>` 포함 **61,531건**, 텍스트가 300자 넘는 건 38,717건뿐이고 그마저 대부분 HTML 스타일. 그런데 현재 파이프라인은 (1) 텍스트에서만 추출해 실데이터에서 건질 게 적고, (2) **비전 OCR을 실제로 돌린 적이 없으며**(OpenAI 비전 클라이언트 미구현), (3) `it_explan` 안에 박힌 스펙 이미지는 커넥터가 HTML 제거 시 **버린다**. 결과적으로 이 제품의 핵심인 *적합성 추천*의 근거 속성이 비어 있다.

## Solution

이미지에서 Functional Attribute를 실제로 추출한다: **OpenAI gpt-4o(vision)** 로 스펙 이미지를 직독하고(ADR-0005), 커넥터가 `it_explan`의 `<img>`까지 이미지로 캡처하며, 트리아지로 대상을 좁혀 비용을 통제한다. 추출된 속성은 `provenance=llm_ocr`(ADR-0004)로 그래프에 저장돼, 재질·용량·온도 등 이미지 기반 적합성 추천이 가능해진다. 수집 오케스트레이터는 이미 `image_extractor`를 호출하므로(이슈 13), 실제 비전 클라이언트 주입 + 트리아지 재설계 + explan 이미지 캡처가 핵심이다.

## User Stories

1. 실험 기획자로서, 나는 스펙이 이미지(스펙표)로만 있는 상품도 그 이미지에서 읽힌 속성으로 추천받고 싶다.
2. 실험 기획자로서, 나는 추천 근거가 이미지에서 왔는지(`llm_ocr`) 텍스트/소스에서 왔는지 구분해 보고 싶다.
3. 운영자로서, 나는 `it_explan` 안에 박힌 스펙 이미지도 누락 없이 처리되기를 바란다.
4. 운영자로서, 나는 모든 갤러리 이미지를 비전에 보내지 않고 트리아지로 **대상을 좁혀 비용을 통제**하고 싶다.
5. 운영자로서, 나는 비전 추출 전에 100건 파일럿으로 **실제 비용을 실측**하고 전체 비용을 예측하고 싶다.
6. 운영자로서, 나는 안 바뀐 상품의 비싼 비전 재호출이 content-hash로 생략되기를 바란다(ADR-0008).
7. 개발자로서, 나는 OpenAI 비전을 `VisionClient` Protocol 뒤에 두어(이슈 10) 테스트에선 가짜로, 운영에선 실제로 교체하고 싶다.
8. 개발자로서, 나는 이미지 유래 속성이 텍스트 유래 속성과 병합될 때 텍스트에서 이미 확정된 차원은 비전 호출에서 생략되기를 바란다(이슈 10 known_names).
9. 개발자로서, 나는 커넥터가 갤러리(it_img1~n)와 explan 임베디드 이미지를 합치되 중복 URL을 제거하기를 바란다.
10. 운영자로서, 나는 비전 실패(이미지 fetch 불가·비정형 응답)가 전체 수집을 멈추지 않고 건너뛰어지기를 바란다.

## Implementation Decisions

- **OpenAIVisionClient** (딥모듈): 이슈 10의 `VisionClient` Protocol을 OpenAI **gpt-4o**(또는 vision 가능 모델, env `OPENAI_VISION_MODEL`)로 구현. 입력=이미지 URL 목록 + 프롬프트, 출력=속성 JSON. 토큰 사용량 누적(비용 산출). 키는 env `OPEN_AI_KEY`. B의 `OpenAILLM`과 같은 사용량 추적 패턴.
- **커넥터 explan 이미지 캡처**: `YoungcartMySQLConnector`가 `it_explan`에서 `<img src>` URL을 파싱해 `ProductDocument.images`에 합류. it_img1~n 갤러리와 합치고 URL 기준 중복 제거. `description_text`는 계속 HTML 제거 텍스트.
- **ImageTriage 재설계**: 파일명 키워드 방식 폐기(실 URL엔 무의미). 기본 전략 = **갤러리 앞쪽 N장(기본 2~3, env 조정) + explan 임베디드 이미지 우선**. content-hash로 재처리 억제(ADR-0008). 전량 비전은 비용상 지양.
- **비전 수집 배선**: `SyncOrchestrator.process_product`는 이미 `image_extractor.extract(product_type, images, known_names)`를 호출한다(이슈 13). 실제 `ImageAttributeExtractor(OpenAIVisionClient)` 를 주입만 하면 됨. 텍스트에서 확정된 속성명은 `known_names`로 비전에서 생략.
- **provenance**: 이미지 유래 속성 `source=llm_ocr`(ADR-0004). 신뢰도 `coerce_confidence`로 견고 처리.
- **비용 파일럿**: 스펙 이미지 있는 상품 100건에 실제 비전 실행, 이미지당 토큰·비용 실측 → 전체 예측(텍스트 B와 동일 방식).
- **견고성**: 이미지 fetch 실패/JSON 파싱 실패는 해당 상품만 건너뛰고 수집 지속.

## Testing Decisions

좋은 테스트는 외부 행동만 검증한다. 비전 실호출은 결정적 더블로 대체.

- **커넥터 explan `<img>` 파싱**: 픽스처 HTML(`<img src=...>` 포함 it_explan)을 넣어 `ProductDocument.images`에 갤러리+explan 이미지가 중복 없이 합쳐지는지. (DB 불필요 단위테스트, 또는 mock source-db 시드에 explan 이미지 포함)
- **ImageTriage 전략**: 이미지 URL 목록 → 선별 결과(갤러리 앞 N + explan 우선)를 검증. prior art: `test_image_extraction.py`.
- **OpenAIVisionClient**: openai 클라이언트를 mock해 배선/사용량 추적만 검증(실 호출 없음). 추출 로직은 기존 `FakeVisionClient`로 이미 커버(이슈 10).
- **수집 통합**: `process_product`에 FakeVisionClient 주입 시 이미지 속성이 `llm_ocr`로 그래프에 병합되는지(기존 test_full_load 확장).

## Out of Scope

- 이미지 자체 호스팅/다운로드 캐싱(초기엔 URL 직접 전달). 접근 불가 이미지는 스킵.
- 비-OpenAI 비전(로컬 OCR 등) — ADR-0005대로 비전 LLM.
- 전체 카탈로그(62.8만) 비전 실행 — 본 PRD는 **100건 파일럿 + 비용 예측**까지. 전량 실행은 배치 설계 별건.
- 스펙표 이미지의 복잡한 레이아웃(병합 셀 등) 완벽 파싱 — best-effort.

## Further Notes

- 비용: 비전은 이미지당 텍스트보다 훨씬 비싸다. 트리아지가 비용의 핵심 레버. 파일럿으로 실측 후 전체 예측.
- 실데이터 확인: 스펙은 압도적으로 이미지에 있음(it_img1 99.99%). ADR-0005의 "절반이 이미지" 가정이 실제로는 "대부분"이었다.
- 커넥터는 스왑 seam(이슈 26)이므로 explan 이미지 캡처는 커넥터 내부 변경으로 다운스트림 불변.
