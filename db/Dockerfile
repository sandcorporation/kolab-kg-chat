# Apache AGE(openCypher) + pgvector 를 한 Postgres 16 인스턴스에 (ADR-0003)
FROM apache/age:release_PG16_1.5.0

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git ca-certificates postgresql-server-dev-16 \
 && git clone --depth 1 --branch v0.8.0 https://github.com/pgvector/pgvector.git /tmp/pgvector \
 && cd /tmp/pgvector \
 && make \
 && make install \
 && rm -rf /tmp/pgvector \
 && apt-get purge -y --auto-remove build-essential git postgresql-server-dev-16 \
 && rm -rf /var/lib/apt/lists/*

COPY initdb/ /docker-entrypoint-initdb.d/
