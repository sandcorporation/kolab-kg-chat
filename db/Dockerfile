# Postgres 16 + pgvector + pg_trgm (ADR-0016: AGE 제거 — 우리 DB엔 임베딩·설명만)
# C(소스 하이드레이션): 상품 사실은 소스에서 채팅 때 하이드레이션하고, 우리 DB는
# 검색 색인(pgvector 시맨틱 + pg_trgm 키워드)만 보관한다. openCypher 그래프 불필요.
FROM pgvector/pgvector:pg16

COPY initdb/ /docker-entrypoint-initdb.d/
