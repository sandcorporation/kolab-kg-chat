# 26 — 실제 kolabshop 커넥터 교체

Status: ready-for-human

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

실제 kolabshop DB가 도착(~2026-06-29)하면 `SourceConnector` 구현을 실제 DB에 맞춰 교체한다(#04의 seam). 영카트 가설이 맞으면 연결 설정 수준, 아니면 실제 스키마에 맞춘 새 구현. **`ProductDocument` 계약과 다운스트림(#06 이후)은 불변.** 동시에 ADR-0002(CDC)의 접근 권한(binlog/WAL)을 확정해 `subscribe_changes`를 실제 CDC로 전환(불가 시 폴링+주기 대조로 후퇴). 실제 자격증명·인프라 결정이 필요하므로 HITL.

## Acceptance criteria

- [ ] 실제 kolabshop DB에 대해 `assemble`/`iter_product_ids`가 `ProductDocument`를 산출
- [ ] 다운스트림(GraphStore·추출·동기화) 코드 변경 없음
- [ ] CDC 접근(binlog/WAL) 확정 → `subscribe_changes`가 실제 변경을 스트리밍 (또는 폴링 fallback 적용)
- [ ] ADR-0002 status를 accepted(또는 폴링 결정)로 갱신
- [ ] 실제 상품 표본으로 전체 적재 + delta 1건 end-to-end 검증

## Blocked by

- `04-source-connector.md`
- 실제 DB 도착 (~2026-06-29)
