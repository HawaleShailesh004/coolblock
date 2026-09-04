# postgis/postgis does not bundle pgvector. This adds it from the same PGDG
# apt repo the base image already trusts, keeping PostGIS + pgvector + PostgreSQL
# version in lockstep with docker-compose.yml's `postgres:16-3.4` pin.
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
