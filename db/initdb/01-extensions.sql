-- 멱등: 재실행해도 안전. C(ADR-0016): 임베딩 검색(vector) + 키워드 검색(pg_trgm)만.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
