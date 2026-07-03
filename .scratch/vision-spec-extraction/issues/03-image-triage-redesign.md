# 03 — ImageTriage 재설계 (실 URL 대응)

Status: ready-for-agent

## Parent

`.scratch/vision-spec-extraction/PRD.md`

## What to build

파일명 키워드("spec"/"dim") 기반 트리아지를 폐기한다(실 URL엔 무의미 — Sigma CDN/`/data/item/...`). 새 전략: **갤러리 앞쪽 N장(기본 2~3, env 조정) + explan 임베디드 이미지 우선**을 비전 대상으로 선별해 비용을 통제한다. explan 이미지(이슈 01)까지 포함해 판단한다.

## Acceptance criteria

- [ ] 갤러리 이미지 중 앞쪽 N장을 대상으로 선별(N은 설정 가능)
- [ ] explan 임베디드 이미지는 우선 대상에 포함
- [ ] 전량이 아니라 상한 내로 선별(비용 통제)되는지 검증
- [ ] 이미지 URL 목록 입력에 대한 결정적 단위 테스트 (prior art: `test_image_extraction.py`)

## Blocked by

- `01-connector-explan-images.md`
