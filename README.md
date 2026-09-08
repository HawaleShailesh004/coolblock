# CoolBlock

> **"Everyone built the map. Nobody built the plan."**
> A block-scale heat-mitigation siting optimizer. You give it a neighborhood
> and a budget. It gives you the ranked parcels, the modeled degrees, the
> people cooled, and the memo you take to city council.

Built for NextStep Hacks 2026 — "Earth Forward". Full design and phase plan:
[`COOLBLOCK-BUILD-PLAN.md`](COOLBLOCK-BUILD-PLAN.md). Architecture notes:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Decisions:
[`docs/adr/`](docs/adr/). **Running it locally and checking that it actually
works: [`docs/RUNNING-AND-TESTING.md`](docs/RUNNING-AND-TESTING.md).**

Locked target: **Edison-Eastlake, Phoenix, AZ** — see
[`config/neighborhood.toml`](config/neighborhood.toml).

## Status

**Phase 8 — frontend core: in progress.** Phases 0-6 are done:

- **0-2**: foundations, the data foundry (all 16 sources, see
  [`docs/DATA-SOURCES.md`](docs/DATA-SOURCES.md)), and the map, first light.
- **3**: the heat engine — TsHARP-downscaled 10m surface temperature,
  validated 2/3, honesty rail applied (see
  [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)).
- **4**: plantable space — rule-based (ML fusion deferred, see
  [`docs/adr/0005-*.md`](docs/adr/0005-plantable-space-rule-first.md)),
  1,481 real polygons, 1,472 candidates with ownership classification.
- **5**: impact & equity — the cooling kernel (C1, locally calibrated),
  shade raytracing (C2), the albedo model (C3), dasymetric population and
  the Heat Vulnerability Index (D1/D2), exposure weighting and the
  Equity-Weighted Cooling Benefit objective (D3/D4).
- **6**: the optimizer — CELF lazy greedy (E2, the production solver),
  exact MILP via HiGHS to measure the approximation ratio, a constrained
  greedy for real side constraints (E3), the efficient frontier (E4), and
  the five-baseline comparison (E5) — **CoolBlock beats TES-score-only by
  4.6-14x** on Equity-Weighted Cooling Benefit at equal budget.

**7**: a real FastAPI service — Postgres-backed plans and scenario
versions, Clerk-shaped auth with a documented local-dev fallback (no
Clerk tenant provisioned yet, see
[`docs/adr/0016-*.md`](docs/adr/0016-auth-dev-fallback-and-clerk-integration.md)),
an ARQ+Redis job queue that runs the real solver and streams its stages
over SSE with clean reconnect, GeoJSON/CSV export, and public share links —
see [`docs/adr/0017-*.md`](docs/adr/0017-phase7-schema-and-job-streaming-architecture.md)
and §8 of [`docs/RUNNING-AND-TESTING.md`](docs/RUNNING-AND-TESTING.md) for
how to run and verify it.

**8 (in progress)**: the live optimizer, wired to that real backend — a
budget slider and constraint controls that create a plan, trigger a real
solve, and stream it onto the map site-by-site over a hand-rolled
`fetch`-based SSE client (`apps/web/lib/sse.ts` — the browser's native
`EventSource` can't send the custom auth headers this app uses), plus a
ranked-sites table (a full peer view of the same data, §8.6), GeoJSON/CSV
export, share links, and a deep-linkable plan/version URL. Two new map
layers: dasymetric population (D1) and the HVI choropleth (D2). Building
this frontend caught and fixed a real bug in Phase 7's SSE endpoint (a
fast client could have its stream closed within milliseconds of
connecting, before the worker even started — see
[`docs/adr/0017-*.md`](docs/adr/0017-phase7-schema-and-job-streaming-architecture.md)'s
amendment) that manual `curl` testing had never caught. Also: real
per-layer loading/error states with a retry action, a table view for
every layer (§8.6), six HVI weight sliders that recompute the choropleth
live client-side from real per-indicator z-scores (§6.4 D2's "a planner
can and should argue with them"), and a real "beats the alternatives"
screen (§9 ★5) — CoolBlock's own solve against all four E5 baselines, at
the scenario's own budget, via a new `/baselines` endpoint. See §9.1 of
[`docs/RUNNING-AND-TESTING.md`](docs/RUNNING-AND-TESTING.md) to verify all
of it.

**10 (started)**: the intelligence layer — L3, the council memo, and L6,
its numeric provenance guard. Claude (opus, "quality, run once") drafts
the memo against this plan's own real, computed data (sites, EWCB,
citations to the five real papers D16 already registered); every number
in the output is then extracted and checked against that same data
(`engine/narrate/provenance.py`), regenerated once if anything fails to
verify, and rendered with a hover showing each number's exact source
(green) or a warning if it still couldn't be verified (amber). The
honesty rail is enforced in the prompt itself, not left to chance: the
heat surface's validation gate didn't clear all three checks (2 of 3, see
`docs/METHODOLOGY.md`), so the model is instructed to say "prioritization
score," never "predicted cooling" — verified live in this session's own
first real generation, which used that exact language unprompted beyond
the rule. That same run also caught and corrected one hallucinated number
via the regeneration path, a live demonstration of L6 doing its job.
**Provider switch added mid-build**
([`docs/adr/0019-*.md`](docs/adr/0019-groq-fallback-provider-for-the-council-memo.md)):
the account's Claude API credit balance ran out partway through this
session's testing, so a second provider (Groq, `openai/gpt-oss-120b`)
was wired in behind the same `generate_council_memo` call — selectable
via `MEMO_LLM_PROVIDER` in `.env` or a per-request `provider` param/UI
dropdown, not a hard swap. Wiring it up surfaced two real, general-purpose
bugs in L6 that Claude's own generations had never triggered (numbers
embedded in citation-title *strings* weren't grounded at all; a candidate
id's hyphen was misread as a unary minus when scanning payload strings) —
both fixed, both apply to either provider. A full real run against a
solved scenario, via the actual API endpoint, converged to zero
unverified numbers with no regeneration needed. Claude remains the
intended default (`.env.example`) once its balance is topped up; Groq is
this build's working fallback in the meantime (`.env`'s
`MEMO_LLM_PROVIDER=groq`).

**L1 added** ([`docs/adr/0020-*.md`](docs/adr/0020-nl-to-constraints-with-real-tool-calls.md)):
natural language to optimizer constraints, via a real, live tool-use loop
(`engine/narrate/constraints_nl.py`), not a free-text parse. A sentence
like *"Keep it to public land only, prioritize sites near Booker T
Washington School, cap annual maintenance at $8,000"* resolves the named
school against the real cached OSM data, pulls the real candidate ids
within 300m of its real coordinates, and returns a schema-validated
constraint set — new `POST /plans/parse-constraints`, wired into
`OptimizerPanel`'s new "Describe constraints" box. Caught and fixed two
real bugs live: a CRS bug (`resolve_place` was returning raw UTM-zone-12N
meters as if they were WGS84 degrees) and a Groq-specific schema
rejection (the model emitted `null` for an empty list field where the
tool schema only allowed an array, a real 400 from Groq's own
server-side validator). A request for something with no real constraint
field (a species-diversity cap, in testing) is disclosed via
`unsupported_requests`, never silently dropped or invented.

**§7.2 verification, closed via the fallback `docs/adr/0002-*.md` already
committed to at Phase 0** (no Wolfram Cloud credential — offered again
this session, still not available):
[`docs/adr/0021-*.md`](docs/adr/0021-engine-verify-without-wolfram.md).
`engine/verify/` now has three real modules, each substituting a specific
non-Wolfram tool for what the plan asked Wolfram to do — `pint` for
unit-checked thermal math (`units.py`, promoting `engine/impact/albedo.py`'s
existing *manual* unit-check comment into code that actually enforces it,
proven by deliberately constructing and catching a real unit error),
`sympy` for symbolic calibration (`sensitivity.py`, a real symbolic
derivative proving beta's confidence interval really does propagate
linearly into ΔT_peak's, not assumed), and the exact MILP solver already
built in Phase 6 (`optimizer_crosscheck.py`, formalizing the
previously-notebook-only 99.6-99.9% CELF-vs-exact measurement as real,
reusable, tested code — including a deliberately-adversarial instance
proving the check can detect real disagreement, not just agreement).
None of this sits on the demo path, matching §7.2's own framing.

**Phase 10 status, per the plan's own MUST/SHOULD/COULD split** (§12.1):
all three SHOULD-tier items (L1, L6, Wolfram verification) are done. L2
(per-site rationale), L4 (grant packet), and L5 (analyst agent) remain
explicitly COULD-tier/roadmap-only, not built in this pass.

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
