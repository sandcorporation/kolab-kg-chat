# 임베딩·시맨틱 검색을 제거하고 그래프 전용 검색으로 간다

배포된 읽기 경로(Recommendation Agent, ADR-0007)는 Knowledge Graph를 **키워드(상품명)·Functional Attribute 필터·Compatibility 순회**로만 검색한다. pgvector 의미 유사도(ADR-0003의 세 질의 축 중 하나, ADR-0009의 임베딩)는 에이전트 도구 어디에도 연결되지 않았고, 실행 인스턴스엔 `kg_embedding` 테이블조차 없다. 이 미사용 역량을 유지할지 정한다.

이 ADR은 **ADR-0009(임베딩 대상·모델)를 대체(supersede)** 하고 **ADR-0003(Postgres+AGE+pgvector)을 개정**한다.

## 결정

- **임베딩·시맨틱(벡터) 검색을 시스템에서 제거**한다. GraphRAG는 이제 그래프 정착(키워드+속성+관계) 검색만을 뜻한다.
- **ADR-0009를 폐기**한다.
- **ADR-0003을 개정**: 질의 모델을 삼중(AGE 순회 + pgvector 유사도 + SQL 필터)에서 **이중(AGE 순회 + SQL/키워드 속성 필터)** 으로 축소한다. pgvector 확장은 더 이상 필요 없다(db 이미지에서 제거 가능).
- 정리 대상 코드: `apps/embeddings`, `apps/sync`의 embed 연결, `Retriever`의 embedder·`retrieve_candidates`, 관련 테스트.

## 이유

- **적합성 신호는 속성·관계에 있다(ADR-0001).** fitness-for-purpose는 정규화된 Functional Attribute와 Compatibility로 결정된다. 벡터 유사도는 근거(Grounding)로 인용할 수 없는 후보를 끌어와 설명가능성 원칙과 충돌한다.
- **키워드+속성+에이전트로 충분하다.** 상품명 토큰 검색(에이전트가 한/영 키워드를 브리징) + 속성 필터 + 관계 순회가 실제로 관련 상품을 회수한다("유리 플라스크"→"투명A급 메스플라스크" 검증됨).
- **비용·복잡도가 순손실이다.** 전 카탈로그 임베딩은 반복 비용(모델 교체 시 전면 재임베딩)과 pgvector 테이블·모델 버전 관리·프로바이더 유지보수를 요구하는데, 읽기 경로가 쓰지 않으니 순비용이다.
- ADR-0009가 노렸던 "비슷한 응용 의미 다리"는 배포 경로에서 구현된 적이 없고, Application·Condition 매칭은 에이전트의 속성 질의로 대체된다.

## 결과

- **롱테일 의미 회수를 상실**한다 — 통제 어휘·상품명 밖 표현은 놓칠 수 있다. 회수율 불만이 실제로 생기면 이 결정을 재검토한다(그때 pgvector를 다시 켠다). 되돌리기 비용이 있으므로 ADR로 남긴다.
- 질의 모델과 인프라가 단순해진다: 단일 Postgres + AGE, pgvector 불필요.
- ADR-0009 무효, ADR-0003의 유사도 축 무효. langgraph 체크포인터/KG 스키마 분리는 그대로 유효하다.
