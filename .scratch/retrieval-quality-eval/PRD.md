# PRD — 리트리벌 스택 검색 품질 ablation

Status: done

## Problem Statement

우리는 추천 챗봇의 리트리벌 스택(그래프·구조 추출·vision·임베딩)이 실제로 **검색 품질에 값을 더하는지**에 대한 실증 근거가 없다. 특히:

- 그래프+추출 파이프라인이 **원시 소스 DB를 LLM이 직접 SQL로 질의**하는 단순 베이스라인보다 나은가?
- **vision LLM**으로 이미지에서 스펙을 뽑는 게(비용 큼) 구조 스펙(field_info)만 쓰는 것보다 나은가?
- **임베딩/시맨틱 검색**이 값을 더하는가? (ADR-0010이 임베딩을 제거했는데, 그 결정이 옳았는지 검증 필요)

근거 없이 아키텍처를 정당화/변경할 수 없다. 또한 vision·임베딩·에이전트·심사는 모두 LLM 비용이라, 실험을 **반복할 때마다 다시 지불하면** 실용적이지 않다.

## Solution

4개 리트리벌 config를 **동일 코퍼스·동일 쿼리·동일 에이전트(프롬프트 고정)** 위에서 돌리고, 강한 LLM 심사가 **블라인드·순서스왑 쌍별 비교**로 어느 쪽이 더 적합한지 판정한다. 결과를 **계층(능력)별 승률**로 집계해 "각 요소가 어디서 값을 더하는가"를 보인다. **모든 비싼 LLM 산출물(vision·임베딩·에이전트 답변·심사 판정)을 캐시**해 재실행은 새 config/쿼리만큼만 비용이 든다.

4개 config (에이전트·프롬프트 고정, 리트리벌만 변경):

1. **SQL 베이스라인** — 원시 소스 DB에 text-to-SQL 도구(읽기전용·LIMIT).
2. **그래프(structured)** — 그래프 도구 + field_info/브랜드(provenance=structured) 속성만 노출.
3. **+vision** — 2 + 구조 스펙 부족 상품에 vision 추출 속성(provenance=llm_ocr) 노출.
4. **+embeddings** — 3 + 상품텍스트 임베딩 + `semantic_search` 도구.

## User Stories

1. 아키텍트로서, 그래프+추출이 원시 SQL 베이스라인보다 추천 품질이 높은지 실증으로 알고 싶다.
2. 아키텍트로서, vision 추출이 구조 스펙 대비 품질을 얼마나 올리는지(이미지-only 상품에서) 알고 싶다.
3. 아키텍트로서, 임베딩/시맨틱 검색이 값을 더하는지 알아 ADR-0010 결정을 검증/갱신하고 싶다.
4. 아키텍트로서, "어느 쿼리 유형(structured/vision/semantic/compatibility)에서 어느 config가 이기는지"를 계층별로 보고 싶다.
5. 평가자로서, 위치편향·config 정체를 모르게(블라인드·순서스왑) 판정해 결과를 신뢰하고 싶다.
6. 운영자로서, vision·임베딩을 한 번만 계산하고 캐시해 반복 실험 비용을 아끼고 싶다.
7. 운영자로서, 에이전트 답변과 심사 판정도 캐시해, config/쿼리를 추가할 때만 새 비용이 들기를 원한다.
8. 평가자로서, 4개 config가 같은 코퍼스·쿼리·에이전트 위에서 공정하게 비교되기를 원한다.
9. 평가자로서, 코퍼스가 차이를 드러낼 케이스(이미지-only, 한/영 미스매치)를 의도적으로 포함하기를 원한다.
10. 평가자로서, 계층화 쿼리셋(능력 태그)이 코퍼스 기반이라 답이 존재하기를 원한다.
11. 개발자로서, config 분리가 데이터 재적재 없이(한 그래프에 다 적재 후 provenance 필터+도구 토글)로 되기를 원한다.
12. 개발자로서, text-to-SQL 도구가 읽기전용·SELECT만·LIMIT 강제로 안전하기를 원한다.
13. 개발자로서, 이 실험이 운영 읽기 경로(ADR-0011)를 바꾸지 않고 격리되기를 원한다.
14. 아키텍트로서, 최종 리포트(config×계층 승률 + 정성 예시 + 결론)를 얻어 다음 아키텍처 결정에 쓰고 싶다.

## Implementation Decisions

- **격리**: 실험은 별도 그래프(예: `eval_graph`)·별도 모듈로 운영 경로와 분리한다. 운영 에이전트/도구(ADR-0011)를 재사용하되 config별로 감싼다.

- **0단계 전제 — 실 데이터 + 코퍼스**: mock(4개)은 부족하므로 `real-source-db`(2.6GB 덤프) 적재가 전제. **EvalCorpus 빌더**(딥모듈)가 실 카탈로그에서 ~200-300 상품을 계층 태그와 함께 선별한다 — 이미지-only(스펙이 이미지에만)·한영 미스매치·모든 Product Type. 선별 결과는 결정적(시드 고정)·영속.

- **누적 적재 + config 필터**: 실험 그래프에 structured + vision 속성을 **모두 적재**하고, config별로 **노출 provenance**를 필터한다 — config 2={structured}, config 3/4={structured, llm_ocr}. 임베딩은 config 4에서만 `semantic_search` 도구로 노출. 재적재 없이 config를 전환한다.

- **RetrievalConfig (딥모듈)**: config_id → (도구 집합, 허용 provenance)로 AgentContext를 구성한다.
  - config 1: `sql_query` 도구만(그래프 도구 없음).
  - config 2: 그래프 도구(provenance={structured}).
  - config 3: 그래프 도구(provenance +llm_ocr).
  - config 4: config 3 + `semantic_search` 도구.

- **text-to-SQL 도구 (딥모듈)**: 소스 스키마(it_name·it_explan·field_info)를 설명받아 에이전트가 SELECT를 생성·실행. 가드레일: 읽기전용 커넥션·SELECT만 허용·LIMIT 강제·타임아웃. 상품 행을 추천 후보로 반환.

- **semantic_search 도구 + lean embeddings (딥모듈)**: Product당 name+설명+속성값을 text-embedding-3-small로 임베딩(pgvector 테이블, ADR-0009 방식 lean 복원). `semantic_search(query,k)`가 top-k 유사 상품 id 반환. **임베딩은 (entity,model,text-hash) 키로 캐시**(idempotent).

- **VisionEnrichment (기존 캐시 재사용)**: 구조 스펙 부족 상품에만 ImageAttributeExtractor 실행, 기존 vision_cache(Postgres+JSON) 재사용. 이미 캐시된 건 재계산 안 함.

- **EvalRunner (딥모듈, 캐시)**: (config_id, query_id, agent_version) 키로 에이전트 답변(rationale+추천 id+grounding)을 캐시 테이블에 저장. 있으면 스킵(LLM 재호출 없음). 에이전트 temp=0, 셀당 1런.

- **Judge (딥모듈, 캐시)**: config 쌍마다 두 답변을 **블라인드**(정체 숨김)로, **A/B 순서를 양방향**으로 심사(위치편향 상쇄). 판정을 (query_id, config_a, config_b, order, judge_model) 키로 캐시. 심사 모델은 강판정(예: gpt-4o).

- **집계·리포트 (딥모듈)**: 순서스왑 판정을 합쳐 무승부/승자 결정 → config×계층 승률 표 + 전체 순위 + 정성 예시. 순수 함수(결정적).

- **캐시 계약**: vision·embedding·agent-run·judge 4계층 모두 캐시. 재실행은 **새 config/쿼리/모델 버전만** 비용 발생. 캐시 무효화는 버전 키(agent_version, judge_model, model)로.

## Testing Decisions

- 좋은 테스트는 **결정적 부분의 외부 동작만** 검증한다(LLM 출력 품질 자체는 심사가 판단; 하네스의 배관을 테스트).
- 테스트 대상(결정적):
  - **EvalCorpus 빌더**: 시드 고정 시 같은 상품·계층 태그 선별(재현성).
  - **RetrievalConfig provenance 필터**: config 2가 llm_ocr 속성을 숨기고 config 3이 노출(get_attributes 결과 차이).
  - **text-to-SQL 가드레일**: 비-SELECT/쓰기 쿼리 거부, LIMIT 강제(주입 방어).
  - **semantic_search**: 가짜 임베더(결정적 벡터)로 top-k 순위 정확.
  - **캐시(embedding/agent-run/judge)**: 미스→계산→히트(재호출 없음), 버전 키 변경 시 무효화. 카운팅 더블로 "캐시 히트 시 LLM 0회" 검증.
  - **Judge 집계**: 순서스왑 판정 합산·무승부 처리·계층 승률 계산(순수 함수).
- 프리아트: `tests/test_agent_tools.py`, `tests/test_ingest_runner.py`, `tests/fake_chat.py`(ScriptedChatModel), 카운팅 커넥션 팩토리(test_graph_batch_session). 도커 내 실제 Postgres+AGE·mock/real source-db.

## Out of Scope

- 운영 읽기 경로(ADR-0011) 변경 — 실험은 격리, 결과는 추후 ADR로 반영.
- 대규모 자동 쿼리 생성, 골드셋 라벨링(쌍별 심사로 갈음).
- Application/Condition 노드 임베딩(구 ADR-0009 풀안) — 상품텍스트 임베딩만.
- 전체 카탈로그 vision/임베딩(코퍼스 서브셋만).
- 사람 평가(정성 스팟체크는 선택).

## Further Notes

- 관련 ADR: 임베딩 제거(ADR-0010, 이 실험이 검증), vision 속성(ADR-0005), 임베딩 대상·모델(ADR-0009, lean 참조), 단일 읽기 경로(ADR-0011), 속성 provenance(ADR-0004).
- 결과가 임베딩/vision의 값을 입증하면 해당 ADR을 갱신(예: ADR-0010 재검토)하는 근거가 된다.
- 코퍼스·쿼리 수(기본 ~250 / ~27)와 심사 모델은 비용에 따라 조절. 캐시 덕에 증분 확장 저렴.
