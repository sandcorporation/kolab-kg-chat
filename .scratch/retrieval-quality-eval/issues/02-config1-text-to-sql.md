# 02 — config 1: text-to-SQL 도구

Status: done — SQLTool(가드+코퍼스 스코핑 eval_items 뷰), 에이전트 SQL도구 일반화, config1 라이브 검증. 테스트 test_sql_tool(6).

## Parent
`.scratch/retrieval-quality-eval/PRD.md`

## What to build

config 1(원시 소스 DB 베이스라인)을 하네스에 얹는다. 에이전트가 소스 스키마(it_name·it_explan·field_info)를 설명받아 **SELECT를 생성·실행**하는 `sql_query` 도구. 가드레일: 읽기전용 커넥션·SELECT만 허용·LIMIT 강제·타임아웃. config 1은 그래프 도구 없이 이 도구만으로 추천 후보를 만든다.

## Acceptance criteria

- [ ] config 1이 코퍼스(=소스 DB의 해당 상품) 위에서 쿼리에 대해 추천을 낸다
- [ ] `sql_query`가 비-SELECT/쓰기 쿼리를 거부하고 LIMIT를 강제한다
- [ ] EvalRunner 캐시가 config 1에도 적용(재실행 시 LLM 재호출 없음)

## Blocked by
- 01 (하네스 골격)
