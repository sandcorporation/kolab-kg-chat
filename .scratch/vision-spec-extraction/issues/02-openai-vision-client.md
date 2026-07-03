# 02 — OpenAIVisionClient

Status: ready-for-agent

## Parent

`.scratch/vision-spec-extraction/PRD.md`

## What to build

이슈 10의 `VisionClient` Protocol을 OpenAI **gpt-4o**(vision, env `OPENAI_VISION_MODEL`로 조정)로 구현한다. 입력=이미지 URL 목록 + 프롬프트 → 속성 JSON 문자열. 토큰 사용량을 누적(B의 `OpenAILLM`과 동일 패턴, `openai_client.py`의 usage 카운터 공유/확장). 키는 env `OPEN_AI_KEY`. 기존 `ImageAttributeExtractor` 뒤에 그대로 끼워진다.

## Acceptance criteria

- [ ] `VisionClient.extract(image_urls, prompt)` 시그니처 구현, 속성 JSON 반환
- [ ] OpenAI 이미지 입력 형식(image_url)으로 URL 목록 전달
- [ ] 토큰 사용량이 usage 카운터에 누적(비용 산출용)
- [ ] `model_version` 노출(예: gpt-4o)
- [ ] openai 클라이언트를 mock한 단위 테스트로 배선·사용량 검증(실 호출 없음)

## Blocked by

None - can start immediately
