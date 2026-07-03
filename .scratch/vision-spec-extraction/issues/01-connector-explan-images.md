# 01 — 커넥터 explan 이미지 캡처

Status: ready-for-agent

## Parent

`.scratch/vision-spec-extraction/PRD.md`

## What to build

`YoungcartMySQLConnector`가 `it_explan` HTML에서 `<img src>` URL을 파싱해 `ProductDocument.images`에 합류시킨다. 갤러리(it_img1~n)와 explan 임베디드 이미지를 합치고 **URL 기준 중복 제거**한다. `description_text`는 계속 HTML 제거 텍스트를 유지한다(스펙은 이미지에 있으므로 텍스트는 보조).

## Acceptance criteria

- [ ] `it_explan`에 `<img src="...">`가 있으면 해당 URL이 `ProductDocument.images`에 포함된다
- [ ] 갤러리(it_img1~n)와 explan 이미지가 합쳐지고 동일 URL은 한 번만 포함
- [ ] explan에 이미지가 없어도(기존 동작) 회귀 없음
- [ ] `description_text`는 여전히 태그 제거된 텍스트
- [ ] 픽스처 HTML(또는 mock 시드의 explan 이미지)로 결정적 테스트

## Blocked by

None - can start immediately
