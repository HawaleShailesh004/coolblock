# CoolBlock

> **"Everyone built the map. Nobody built the plan."**
> A block-scale heat-mitigation siting optimizer. You give it a neighborhood
> and a budget. It gives you the ranked parcels, the modeled degrees, the
> people cooled, and the memo you take to city council.

Built for NextStep Hacks 2026 — "Earth Forward". Full design and phase plan:
[`COOLBLOCK-BUILD-PLAN.md`](COOLBLOCK-BUILD-PLAN.md). Architecture notes:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Decisions:
[`docs/adr/`](docs/adr/).

Locked target: **Edison-Eastlake, Phoenix, AZ** — see
[`config/neighborhood.toml`](config/neighborhood.toml).

## Status

**Phase 4 — Plantable space: complete.** Phases 0 (foundations), 1 (data
foundry — all 16 data-contract sources, see
[`docs/DATA-SOURCES.md`](docs/DATA-SOURCES.md)), 2 (the map, first light),
and 3 (the heat engine — validated 2/3, honesty rail applied, see
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)) are done. The rule-based
plantable-space layer (ML fusion deferred, see
[`docs/adr/0005-*.md`](docs/adr/0005-plantable-space-rule-first.md))
identifies 1,481 real polygons (301 ha, 52% of the neighborhood) from
NAIP, OSM buildings/roads/parking/trees, generating **1,472 candidates**
(street trees, tree clusters, shade structures) with real ownership
classification. A manual spot-check against aerial imagery found and
fixed a real gap (untagged parking lots) and disclosed a residual 6.7%
error rate from OSM data completeness — see
[`notebooks/02-plantable-space.ipynb`](notebooks/02-plantable-space.ipynb).
Toggle "Plantable space" at `/map` to see it live. The impact/equity model
and the optimizer (Phases 5-9) are next — see the plan's 16 phases.

## Quickstart

Prerequisites: Node ≥ 20, pnpm ≥ 9, Python 3.11–3.12, [`uv`](https://docs.astral.sh/uv/),
Docker Desktop (or a Docker daemon).

```bash
cp .env.example .env
make dev
```

This brings up Postgres+PostGIS+pgvector, Redis, MinIO (a local stand-in for
Cloudflare R2), and TiTiler via Docker Compose, installs JS and Python
dependencies, and starts the Next.js app + FastAPI dev servers.

- Web: http://localhost:3000
- Map: http://localhost:3000/map (first run: `uv run python scripts/export_map_layers.py`,
  `bash scripts/build_basemap.sh`, and `uv run python scripts/export_heat_surface.py`
  to populate `data/derived/edison-eastlake/` and MinIO)
- API: http://localhost:8000/health
- MinIO console: http://localhost:9001

If port 8000 is already taken by something else on your machine, run
`API_PORT=8001 make dev` and update `NEXT_PUBLIC_API_URL` in `.env` to match.

**No `make` on Windows?** Install it (`choco install make` or `scoop install make`)
or run the Makefile's steps directly: `docker compose up -d --wait`, then
`pnpm install && uv sync --all-packages --all-extras`, then `bash scripts/dev.sh`.

Individual pieces:

```bash
make up          # infra only (Postgres, Redis, MinIO, TiTiler)
make install      # JS + Python deps
make lint         # ESLint + ruff
make typecheck    # tsc --noEmit + mypy
make test         # JS + Python test suites
make ingest       # engine.ingest — Phase 1
```

## Repo layout

See COOLBLOCK-BUILD-PLAN.md §3.4 for the annotated version.

```
coolblock/
├─ apps/web/       Next.js 15 — marketing + app
├─ apps/api/       FastAPI — REST + SSE + job control
├─ packages/ui/     design system: tokens, primitives, motion
├─ packages/map/    MapLibre + deck.gl layer library
├─ packages/schema/ shared TS types generated from Pydantic/OpenAPI
├─ engine/          the science — installable Python package
├─ data/            versioned cache + derived pipeline outputs
├─ config/          neighborhood.toml — the scope lock
├─ notebooks/       validation + calibration, committed with outputs
└─ docs/            architecture, methodology, data sources, ADRs
```

## The No-Fake Rule

Nothing in CoolBlock is simulated for effect — no hardcoded "results," no
artificial delays, no placeholder charts, no dead buttons. The one sanctioned
exception is demo-mode: cached artifacts of real data, computed by the real
pipeline, frozen for reproducibility and labeled as such. See
COOLBLOCK-BUILD-PLAN.md §1.1.
