# 14 — SyncOrchestrator: delta (코얼레싱 + content-hash)

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

delta 반영 경로(ADR-0008). `subscribe_changes()`(지금은 Mock Source DB 폴러, 월요일 실제 CDC로 교체 — #26)가 변경을 신호로 내면, **Product 단위로 코얼레싱/디바운스**(느슨한 지연 허용)하여 한 번만 재처리. 워커는 이벤트를 재생하지 않고 **현재 상태 재조립**(멱등). **content-hash 게이팅**으로 안 바뀐 부분의 비싼 비전 LLM 재호출 생략.

## Acceptance criteria

- [ ] 한 Product에 변경 버스트 → 디바운스 창 내 **재추출 1회**
- [ ] 워커가 현재 상태를 재조립(이벤트 페이로드 재생 아님)
- [ ] content-hash 동일 → 추출 스킵(특히 비전 LLM 미호출)
- [ ] 가격만 변경 → 비전 재호출 없이 가격만 갱신
- [ ] 삭제 변경 → 그래프에서 해당 Product 제거
- [ ] 폴러는 `SourceConnector.subscribe_changes` 인터페이스 뒤에 있어 CDC로 교체 가능

## Blocked by

- `13-sync-initial-full-load.md`
