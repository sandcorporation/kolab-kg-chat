# 04 — RagRecommender 리랭크 스테이지 (리랭커 주도)

Status: ready-for-agent

## Parent

`.scratch/rerank-query-normalization/PRD.md`

## What to build

검색과 선택 사이에 리랭크를 삽입해 end-to-end로 흐르게 한다:

```
analyze → retrieve(50) → rerank → 점수≥2 & top-10 → select(유형필터 + 근거)
      ↑ 불만족(≥2 후보 전무 or 선택이 전부 유형불일치) → 검색어 재정식화 후 재시도
```

리랭커가 결과 집합을 **주도**하고, 선택 LLM은 명백한 유형 불일치 제거와 근거 작성으로 강등된다.
`≥2` 후보가 하나도 없으면 반복 루프가 검색어를 바꿔 재시도한다("선택: 없음" 유지 + 새 트리거).
리랭크는 매 반복에 적용하되, 후보 수가 상한 이하이면 스킵한다. 리랭커는 생성자로 주입한다
(`RagRecommender(model, retriever, analyzer, reranker)`).

## Acceptance criteria

- [ ] 검색 후보가 리랭크되어 점수≥2 & 최대 10만 선택 단계로 전달됨
- [ ] 넓은 유형 질의("집게")에서 집게류 여럿이 상위로(리콜 역전 해소, 단독 검증)
- [ ] `≥2` 후보 전무 시 재검색으로 재시도(반복 루프 유지)
- [ ] 선택 LLM이 유형 불일치는 제거하되 랭킹·결과 집합을 좌우하지 않음
- [ ] 후보 수 ≤ 상한이면 리랭크 콜 스킵
- [ ] FakeReranker + FakeRetriever + fake 모델로 플로우·재시도·강등을 결정적으로 테스트

## Blocked by

- `.scratch/rerank-query-normalization/issues/01-reranker-deep-module.md`
- `.scratch/rerank-query-normalization/issues/02-candidate-registry-values.md`
