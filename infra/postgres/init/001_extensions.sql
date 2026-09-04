-- Enabled once, at container init, on a fresh volume.
-- Alembic migrations (Phase 7) own the schema; this file only owns extensions.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
