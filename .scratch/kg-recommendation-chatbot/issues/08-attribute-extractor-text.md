# 08 — AttributeExtractor (텍스트)

Status: ready-for-agent

## Parent

`.scratch/kg-recommendation-chatbot/PRD.md`

## What to build

`ProductDocument` → **Product Type 분류** → 그 유형의 통제 어휘(#05)로 **Functional Attribute 추출**(텍스트: description_text + 변형 라벨). 모든 속성에 **provenance(`structured`/`llm_text`) + confidence** 부착(ADR-0004). LLM은 자율 결정(사람 게이트 없음), 테스트는 결정적 가짜 LLM 더블(embed-chat `fake_llm` 선례). 추출 결과를 그래프 노드 속성으로 upsert.

## Acceptance criteria

- [ ] 메스플라스크 → 유형=유리/소모품, 재질/용량 속성 추출(provenance 포함)
- [ ] D₂O → 유형=시약, 순도/CAS/포장 속성 추출
- [ ] 소스 컬럼 직결 값은 `structured`, 텍스트 추출 값은 `llm_text`로 태깅
- [ ] 각 속성에 confidence 기록
- [ ] 가짜 LLM으로 고정 입력 → 기대 속성 집합 검증(외부 행동만)
- [ ] 추출 속성이 GraphStore에 멱등 upsert됨

## Blocked by

- `05-controlled-vocabulary-seed.md`
- `07-ingestion-tracer.md`
