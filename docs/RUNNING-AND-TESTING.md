# Running & testing CoolBlock locally

Everything below has actually been run during Phases 0–4 — this isn't a
theoretical quickstart, it's the exact sequence used to verify each phase.
If a step doesn't match what you see, that's a real bug worth reporting,
not "works on my machine."

## 1. Prerequisites

- Node ≥ 20, [pnpm](https://pnpm.io/) ≥ 9
- Python 3.11–3.12, [`uv`](https://docs.astral.sh/uv/)
- Docker Desktop (or any Docker daemon) — **must be running** before step 2
- [Go](https://go.dev/) — only needed once, to build the `go-pmtiles` CLI (basemap extraction)

## 2. One-time setup

```bash
cp .env.example .env
pnpm install
uv sync --all-packages --all-extras
```

Add a **Census API key** to `.env` (`CENSUS_API_KEY=...`) — free, instant,
at <https://api.census.gov/data/key_signup.html>. Everything else in
`.env.example` already has working local defaults.

## 3. Bring up local infra

```bash
docker compose up -d --wait
```

This starts Postgres 16 + PostGIS + pgvector, Redis, MinIO (a local
stand-in for Cloudflare R2), and TiTiler. Verify all four are healthy:

```bash
docker compose ps
```

You should see `coolblock-minio`, `coolblock-postgres`, `coolblock-redis`
all `(healthy)`, and `coolblock-titiler` `Up` (it has no healthcheck
defined, that's expected).

**If Docker Desktop isn't running**, start it first — on Windows/Mac this
is a normal application; `docker compose up` will fail with a "pipe not
found" style error otherwise.

## 4. Run the data pipeline (Phase 1)

This fetches all 16 data-contract sources for Edison-Eastlake, Phoenix
from live APIs (Planetary Computer, Census, CDC, Maricopa County, Open-Meteo,
NASA POWER, etc.) and caches them under `data/cache/`. It's idempotent —
safe to re-run; already-cached sources are skipped.

```bash
uv run python -m engine.ingest.run_all
```

First run takes several minutes (real network fetches — Landsat alone
pulls 63 scenes). A clean re-run (everything already cached) completes in
under 10 seconds. Check `docs/DATA-SOURCES.md` for what each source gives
you and its current status.

**Verify it worked:**

```bash
uv run pytest engine/tests -q
```

You should see all tests pass (31+ tests, more each phase — currently 44).
Tests for a source that isn't cached are skipped, not failed, so a partial
ingest still gives you a green run for what *is* there.

## 5. Run the science pipeline (Phases 3–4)

These compute on top of the Phase 1 cache — no network calls, just local
ML/geospatial processing. Nothing is pre-baked; every number is computed
live from what `run_all` fetched.

```bash
# Phase 3: the heat surface (composite, TsHARP downscaling, validation)
uv run python -c "from engine.thermal.validate import run_validation; v = run_validation(); print(v.passed, v.reasons)"

# Phase 4: plantable space + candidates
uv run python -c "from engine.surface.candidates import generate_candidates; print(len(generate_candidates()), 'candidates')"
```

Or just open the notebooks (see §8) — they run the same code and show the
actual figures.

## 6. Export data for the map app

Three one-off scripts populate `data/derived/edison-eastlake/` and MinIO.
Re-run any of them whenever the underlying data changes.

```bash
# Buildings, roads, parcels, candidates, the demo optimizer selection, and
# (Phase 8) dasymetric population + the HVI choropleth -> GeoJSON
uv run python scripts/export_map_layers.py

# The basemap: a ~4MB neighborhood-scoped extract from Protomaps' public
# build, uploaded to MinIO. Needs go-pmtiles: `go install github.com/protomaps/go-pmtiles@latest`
bash scripts/build_basemap.sh

# The Phase 3 heat surface as a Cloud-Optimized GeoTIFF, uploaded to MinIO for TiTiler
uv run python scripts/export_heat_surface.py
```

## 7. Start the app

```bash
bash scripts/dev.sh
```

This starts both the FastAPI server and the Next.js dev server together
(and stops both on Ctrl-C). If port 8000 is already taken by something
else on your machine:

```bash
API_PORT=8001 bash scripts/dev.sh
```

(and update `NEXT_PUBLIC_API_URL` in `.env` to match, if you're using the
API directly — the map page doesn't need it yet).

No `make` on Windows? Run the pieces directly instead of `make dev`:
`docker compose up -d --wait`, then `pnpm install && uv sync --all-packages --all-extras`,
then `bash scripts/dev.sh` — that's exactly what `make dev` does.

### What to open

| URL | What it is |
|---|---|
| <http://localhost:3000> | Marketing homepage (light theme) — mostly a placeholder still |
| **<http://localhost:3000/map>** | **The actual product.** Everything below is here. |
| <http://localhost:8000/health> (or 8001) | API health check — confirms the FastAPI backend is up |
| <http://localhost:9001> | MinIO console (login: `coolblock` / `coolblock123`) — browse uploaded tiles/COGs |
| <http://localhost:8090/cog/info?url=s3://coolblock-data/heat_surface_lst.tif> | TiTiler serving the heat surface COG directly |

## 8. The backend: plans, solves, and migrations (Phase 7)

`bash scripts/dev.sh` starts the FastAPI app but not its database schema or
its job worker — those are one-time/separate steps.

```bash
# Apply the Postgres schema (workspaces, plans, scenario versions, sites,
# share links, annotations, audit log) — run once, and again after any
# migration is added.
cd apps/api && uv run alembic upgrade head && cd ../..

# Start the ARQ worker that actually runs solves (separate process from
# the API — the API only enqueues; nothing about a solve blocks a request).
cd apps/api && uv run arq coolblock_api.jobs.worker.WorkerSettings
```

No Clerk credentials are provisioned yet (`docs/adr/0016-*.md`), so every
request needs `X-Dev-User-Id` / `X-Dev-Workspace-Id` (and optionally
`X-Dev-Role`, default `owner`) headers instead of a real bearer token —
refused automatically if `ENVIRONMENT=production`. **The Phase 7
checkpoint, verified**:

```bash
# Create a plan, kick off a solve, and watch its real pipeline stages
# stream in over SSE:
PLAN=$(curl -s -X POST localhost:8000/plans \
  -H 'Content-Type: application/json' -H 'X-Dev-User-Id: alice' -H 'X-Dev-Workspace-Id: org-a' \
  -d '{"name":"Demo","budget_usd":50000}')
PLAN_ID=$(echo "$PLAN" | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
SOLVE=$(curl -s -X POST "localhost:8000/plans/$PLAN_ID/solve" -H 'X-Dev-User-Id: alice' -H 'X-Dev-Workspace-Id: org-a')
VERSION=$(echo "$SOLVE" | python -c "import sys,json;print(json.load(sys.stdin)['version_number'])")
curl -N "localhost:8000/plans/$PLAN_ID/scenarios/$VERSION/events" -H 'X-Dev-User-Id: alice' -H 'X-Dev-Workspace-Id: org-a'
```

You should see `stage` events (`loading_candidates` → `scoring_impact` →
`solving`), then a `site` event per selected site in ranked order, then
one `done` event — the ARQ worker terminal shows the same job being
picked up and completed. Once done,
`GET /plans/$PLAN_ID/scenarios/$VERSION` returns the persisted result,
`.../export.geojson` and `.../export.csv` return the sites, and
`POST .../share` + `GET /share/{token}` (no auth needed) expose a public
read-only view.

**Regenerate the frontend's TypeScript API types** after changing any
router/schema (the API must be running):

```bash
API_URL=http://localhost:8000 pnpm --filter @coolblock/schema generate
```

## 9. What to actually check on `/map`

This is the real verification checklist — what "it works" means concretely:

1. **The map loads in 3D** with a dark basemap, tilted camera, real street
   grid. If it's blank/white, check the browser console — the most common
   cause is `basemap.pmtiles` not uploaded yet (step 6).
2. **Left rail, "Layers"** — five toggles, each with a live count next to
   it once data loads (a few seconds): Roads (2,734), Parcel boundaries
   (2,956), Plantable space (1,472), Buildings (2,844), Heat surface.
   - **Buildings**: real 3D extrusion. Click one — the right panel
     ("Inspector") shows `building_type`, `height_m`, and
     `height_provenance` (`measured` / `levels` / `estimated_default` —
     most will be `estimated_default`, that's expected and disclosed).
   - **Heat surface** (on by default): a glowing inferno-colored raster
     under the buildings. This is the real, validated (2/3 checks — see
     `docs/METHODOLOGY.md`) downscaled surface temperature.
   - **Plantable space** (off by default — toggle it on, turn Heat
     surface off to see it clearly): the neighborhood should "light up"
     in cyan/green/orange in the gaps between buildings. Click a colored
     polygon — the Inspector shows `intervention_type`, `ownership`,
     `capacity`, `total_cost_usd`.
3. **Command palette**: press `Cmd+K` (Mac) or `Ctrl+K` (Windows/Linux).
   Try "Show layer: ..." / "Hide layer: ..." commands, "Reset camera to
   default view", and "Copy shareable link to this view" — paste the
   clipboard content into a new tab and confirm it restores the same
   camera position.
4. **Pan/zoom the map**, then reload the page — the camera should return
   to where you left it (state lives in the URL's `?map=` parameter).

If all four of those work, everything built through Phase 4 is verified
end to end, not just "the code exists."

### 9.1 The live optimizer panel (Phase 8)

Requires the real backend running (§8: API + `alembic upgrade head` +
the ARQ worker), not just the static-file layers above.

1. **Rightmost panel, "Optimizer"** — a budget slider ($5k–$500k), a
   "Public land only" toggle, a "Max sites per block group" field, and a
   **Run optimizer** button.
2. Click **Run optimizer**. The status line should show live stage
   messages ("Loading the cached, pre-scored candidate universe" →
   "Building the equity-weighted coverage objective (D4)" → "Running CELF
   cost-effective greedy (E2)"), then sites landing on the map **one at a
   time** — white-outlined polygons appearing in ranked order — with a
   running "site N · $X of $budget" counter, finishing with a green
   summary line (site count, total cost, total EWCB, solver name).
3. **Click a landed site on the map** — the Inspector shows its rank,
   intervention type, cost, and EWCB contribution, same as any other
   layer (no special-cased UI for this).
4. **The ranked-sites table** below the button lists every selected site
   (rank, type, cost, marginal EWCB) — a full peer view of the same data
   the map shows, readable with no map at all (§8.6).
5. Once done, **reload the page** — the plan/version deep-link in the URL
   (`?plan=...&version=...`) should restore the exact same ranked result
   without re-solving.
6. **Export GeoJSON / Export CSV / Share link** — all three should work;
   the share link should open in a private/incognito window (no auth)
   and show the same result read-only.
7. Toggle **"Dasymetric population (D1)"** and **"Heat Vulnerability
   Index (D2)"** in the left rail — the population layer should shade
   residential buildings by modeled occupancy, and the HVI layer should
   colour block groups on a teal (below-average vulnerability) to red
   (above-average) scale, both toggleable independently of the live
   optimizer run.
8. **Left rail, "Equity weights (HVI, D2)"** — six sliders (default 1.0
   each). Check "Show weighted HVI on map", then drag one slider — the
   choropleth should visibly recolor live (no network request; it's
   recomputed client-side from the real per-indicator z-scores). "Reset
   to equal weights" should appear once any slider moves and should
   restore the default coloring when clicked.
9. **After a solve completes, "Beats the alternatives?"** — click
   **Compare vs. baselines** (takes ~15-20s, real compute: it re-samples
   the actual downscaled LST raster). A five-bar chart appears; CoolBlock
   should be the longest bar by a wide margin (measured 4.6-14x over
   TES-score-only across budgets — see `docs/METHODOLOGY.md`).
10. **"Council memo"** — requires either `ANTHROPIC_API_KEY` (Claude,
    higher quality, ~15-60s) or `GROQ_API_KEY` (Groq, `openai/gpt-oss-120b`,
    much faster, ~3-8s) set in `.env` with a positive credit balance; the
    **Model** dropdown above the button picks which one to use for that
    call, overriding `.env`'s `MEMO_LLM_PROVIDER` default
    ([`docs/adr/0019-*.md`](docs/adr/0019-groq-fallback-provider-for-the-council-memo.md)).
    Click **Generate council memo** (longer if L6's provenance guard has
    to trigger one regeneration). The memo should use "prioritization
    score" language for any cooling/temperature claim, never "predicted
    cooling" (the honesty rail, enforced in the prompt). Hover any
    underlined number: green means it traced back to this plan's real
    data (a tooltip names the exact field); amber means L6 could not
    verify it even after a retry. A 502 error here (`credit balance is
    too low`) means the selected provider's account needs billing/credits,
    not a bug in this feature — try the other provider from the dropdown.
11. **"Describe constraints"** (§7.1 L1,
    [`docs/adr/0020-*.md`](docs/adr/0020-nl-to-constraints-with-real-tool-calls.md))
    — type e.g. `Keep it to public land only, prioritize sites near
    Booker T Washington School, cap annual maintenance at $8,000` and
    click **Parse with AI** (takes a few seconds; real API cost, rate
    limited 5/min/workspace). The public-land checkbox, maintenance-cap
    field, and a green line naming the resolved school and how many real
    nearby sites were included should all update. A place that can't be
    found in the local map data is reported in amber, never silently
    dropped. Running the optimizer afterward should actually include
    those sites in the solve — the parsed constraints round-trip into the
    real solver exactly like a manually-entered one.

## 10. Automated checks

```bash
# Python: tests, lint, types
uv run pytest -q          # engine/tests + apps/api/tests together
uv run ruff check .
uv run mypy engine apps/api/src

# JS: lint, types, build
pnpm turbo run lint typecheck build
```

`apps/api/tests` needs the same Postgres/Redis containers from §3 running
(it creates its own `coolblock_test` database and uses Redis logical DB 1,
both on the same containers, so it never touches your `coolblock`
dev data) — no other setup is required, `apps/api/tests/conftest.py`
handles it. These tests are skipped, not failed, if
`data/derived/edison-eastlake/candidates.geojson` hasn't been built yet
(§6) — the solve/export/share tests need it.

**The council-memo and constraint-parsing tests cost a real LLM API call
and are skipped by default.** Set `RUN_LLM_TESTS=1` to run them (e.g.
before a demo, or after touching `engine/narrate/`) — they run against
whatever `MEMO_LLM_PROVIDER` resolves to in `.env` (`anthropic` or
`groq`; see
[`docs/adr/0019-*.md`](docs/adr/0019-groq-fallback-provider-for-the-council-memo.md)),
so run twice with each set to cover both providers:

```bash
RUN_LLM_TESTS=1 uv run pytest engine/tests/test_memo_live.py apps/api/tests/test_memo_endpoint_live.py engine/tests/test_constraints_nl.py -q
```

All of these are expected to be clean on `main` at all times — if one
fails after pulling latest, that's a regression, not a "known issue."

## 11. Notebooks (the executed, evidence-carrying checkpoints)

These aren't scratch files — each is committed *with its outputs*, so you
can read the real numbers and figures without re-running anything:

- `notebooks/00-phase1-data-check.ipynb` — all 16 data sources, aligned
- `notebooks/01-thermal-validation.ipynb` — the heat surface + the A3 validation gate's actual result
- `notebooks/02-plantable-space.ipynb` — plantable space + the candidate spot-check

Open with `jupyter lab notebooks/` (or your editor's notebook viewer) to
read them, or re-execute with:

```bash
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/<name>.ipynb
```

## Troubleshooting

- **Docker containers "unhealthy" or connection refused on 5433/6379/9000/8090**:
  Docker Desktop may have stopped (it does on some machines after being
  idle for hours). Restart Docker Desktop, then `docker compose up -d --wait` again.
  Data in named volumes (Postgres, MinIO) survives a restart.
- **Postgres connection refused/auth fails even though the container is
  healthy**: check whether something else on your machine is already
  bound to the port Postgres uses. This project maps the container to
  host port **5433**, not the default 5432, specifically because some
  machines have a native Postgres install already listening on 5432 --
  `docker exec` into the container still works in that case (it bypasses
  host port forwarding), only host-side connections silently hit the
  wrong Postgres and fail auth.
- **`/map` shows buildings/roads but no basemap (solid black/blank)**:
  `basemap.pmtiles` isn't in MinIO yet — run `bash scripts/build_basemap.sh`.
- **Heat surface layer doesn't render**: the COG isn't in MinIO or TiTiler
  can't reach it — run `scripts/export_heat_surface.py`, then check
  `curl http://localhost:8090/cog/info?url=s3://coolblock-data/heat_surface_lst.tif`
  returns real bounds/stats, not an error.
- **A layer's count stays at "..." forever**: its GeoJSON export is
  missing or stale — re-run `scripts/export_map_layers.py`.
- **Port 8000 (or 3000) already in use**: something unrelated on your
  machine owns it. Use `API_PORT=8001 bash scripts/dev.sh` for the API;
  for the web port, run `pnpm exec next dev -p 3001` directly from `apps/web`.
- **`uv sync` fails to build `coolblock-engine`**: make sure you're
  running it from the repo root (not `engine/`) — the root `pyproject.toml`
  *is* the engine package (see `docs/ARCHITECTURE.md`).
