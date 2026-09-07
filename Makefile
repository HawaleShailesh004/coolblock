.PHONY: dev up down logs install ingest lint typecheck test clean db-shell

# Bring up the full local stack: infra containers + JS dev servers + API dev server.
# DoD (Phase 0): `make dev` brings up the full stack on a clean machine.
# API_PORT overrides the default :8000 if something else on your machine already owns it.
dev: up install
	bash scripts/dev.sh

# Infra only: Postgres+PostGIS+pgvector, Redis, MinIO (local R2), TiTiler.
up:
	docker compose up -d --wait

down:
	docker compose down

logs:
	docker compose logs -f

install:
	pnpm install --frozen-lockfile || pnpm install
	uv sync --all-packages --all-extras

# DoD (Phase 1): `make ingest` on a clean machine produces a byte-identical cache.
# Idempotent and resumable -- see engine/ingest/manifest.py.
ingest:
	uv run python -m engine.ingest.run_all

lint:
	pnpm turbo run lint
	uv run ruff check .

typecheck:
	pnpm turbo run typecheck
	uv run mypy .

test: # needs `make up` running -- apps/api/tests provisions its own coolblock_test DB on the same Postgres container
	pnpm turbo run test
	uv run pytest

clean:
	pnpm turbo run clean
	docker compose down -v
	rm -rf node_modules

db-shell:
	docker compose exec postgres psql -U coolblock -d coolblock
