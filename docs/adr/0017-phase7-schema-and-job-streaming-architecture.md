# 17. Phase 7 schema, warm-solve service boundary, and SSE reconnect design

Date: 2026-09-08

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §10 Phase 7 asks for a real product surface:
"FastAPI: plans, scenarios, sites, constraints, exports, share links,"
"ARQ workers + Redis; SSE progress streaming with named pipeline stages,"
and a DoD that includes "SSE reconnects cleanly on drop." §4.1 also
establishes the architectural premise this phase has to respect: "the
expensive geospatial work is precomputed per neighborhood. What the user
triggers is only the optimizer over a prepared candidate set."

Several concrete design decisions had to be made building this.

## Decision

### 1. The warm-solve path reads the cached candidate export, not `engine` from scratch

`engine/optimize/plan_service.py` (new) reads
`data/derived/edison-eastlake/candidates.geojson` -- the file
`scripts/export_map_layers.py`'s `export_candidates()` already produces --
rather than recomputing C1-C3/D1-D4 per request. That recomputation is
the "cold pipeline" (20-90 min, §4.1); running it per budget-slider drag
would contradict the plan's own stated architecture. `NEIGHBORHOOD_SLUG`
is a literal `"edison-eastlake"` matching the export script's own `OUT_DIR`
constant, not a second lookup keyed off `config/neighborhood.toml`'s `id`
field -- the scope lock (§1.3) means exactly one of these exists for the
life of this build, so a second source of truth for the directory name
would only be a place for the two to drift apart.

### 2. One `stream_solve()` generator, shared by the API worker and any future caller

`plan_service.stream_solve()` automatically picks E2's CELF (`engine.optimize.celf.solve`)
when only a plain budget cap is set, or E3's constrained greedy
(`engine.optimize.constraints.constrained_greedy`) when any side
constraint is active -- matching each solver's own documented scope
exactly, not reimplementing either. `constrained_greedy`'s `ConstrainedResult`
gained a `picks: list[Selection]` field (reusing CELF's own `Selection`
record type) specifically so the constrained path can also animate
site-by-site, in true commit order, the same way CELF's generator always
could -- a small, targeted addition to Phase 6 code, not a Phase 7-only
side file, because both solvers now hand the caller the same shape.

### 3. `Workspace.id` is Clerk's own org id; `ScenarioSite` is a real PostGIS table

Recorded in full in `docs/adr/0016-*.md` and `db/models.py`'s own module
docstring. In short: no second, locally-minted UUID for a workspace when
Clerk's `org_id` already is one; sites get their own row (with a real
`geoalchemy2.Geometry` column) rather than being a JSON blob on
`ScenarioVersion`, since the export/table-view endpoints need per-site
rows regardless and this stack's whole reason for choosing
Postgres+PostGIS (§3.3) is spatial data belongs in spatially-queryable
rows.

### 4. SSE reconnect: a durable Redis list *and* a pubsub channel, subscribe-before-replay

`coolblock_api/jobs/events.py`: every event is `RPUSH`ed onto
`job:{id}:events` *and* published on `job:{id}:channel`. Pure pubsub
loses anything published before a subscriber connects or during a
dropped connection -- exactly the DoD's "reconnects cleanly" requirement.
The SSE endpoint (`routers/scenarios.py`) **subscribes to the channel
before reading the replay list**, not after -- subscribing first closes
the race where an event lands in the gap between "read the list" and
"start listening," which would otherwise be silently missed by both
paths. A `seq <= already-seen` check on the live side de-duplicates the
one event that can now arrive by both paths.

### 5. The CPU-bound solve is bridged into the async worker via a real background thread

`coolblock_api/jobs/thread_bridge.py::iterate_in_thread` runs
`stream_solve()` (synchronous, CPU-bound geopandas/numpy) in a real OS
thread and forwards each yielded item to the ARQ task's event loop via
`loop.call_soon_threadsafe`. The alternative, `asyncio.to_thread(list, generator)`,
would run the whole generator to completion before yielding anything --
defeating the entire point of an incremental SSE stream (§9 ★2: "the
algorithm genuinely emits sites in that order").

### 6. `get_redis()` caches per event loop, not process-wide

A real bug caught building `apps/api/tests`: a single process-wide cached
`redis.asyncio.Redis` client, reused across `TestClient`'s own internal
event loop (an anyio portal in a background thread) and `pytest-asyncio`'s
per-test loop, hung indefinitely rather than raising -- a future tied to
one loop, awaited from another, that never gets a callback fired.
`coolblock_api/jobs/redis.py` now caches one client per `id(running_loop)`.
In production there is exactly one long-running loop for the process's
life, so this has no behavioral difference there; it only changes
behavior in a multi-loop test process, which is precisely where the bug
was.

## Consequences

- A scenario version's `job_id` is minted by `routers/plans.py::solve_plan`
  *before* enqueueing (`_job_id=job_id` passed explicitly to
  `pool.enqueue_job`), not left to ARQ to generate -- so it can be
  returned to the caller in the same response that creates the
  `ScenarioVersion` row, and the SSE endpoint can look it up from that row
  without a second round trip.
- `apps/api/tests` run against a dedicated `coolblock_test` Postgres
  database and a separate Redis logical DB (index 1) on the same local
  containers, truncated/flushed before every test -- real infra, not
  mocks, per this project's own "No-Fake Rule" (§1.1), without clobbering
  whatever a developer has loaded in the `coolblock` database via `/map`.
- The five-baseline comparison (E5) is now exposed as
  `GET /plans/{plan_id}/scenarios/{version}/baselines` (Phase 8, §9 ★5) --
  `engine.optimize.plan_service.run_baseline_comparison` runs it via
  `asyncio.to_thread` (real cost, ~15-20s, dominated by `worst_first`
  sampling the actual downscaled LST raster) so it doesn't block the
  event loop, rate-limited like the solve endpoint. The efficient
  frontier (E4) still runs offline/notebook-side (Phase 6, unchanged);
  that wiring (★4, an instant lookup against a precomputed budget sweep)
  is still open.
- **Descoped, disclosed rather than silently dropped**: PMTiles generation
  for the API's own vector layers (candidates/sites, as opposed to the
  basemap) is not built this phase. At current data volumes (a few
  thousand features per layer), `deck.gl`'s `GeoJsonLayer` over the plain
  JSON the existing `/api/layers/[name]` route already serves is well
  within the plan's own "20k features at 60fps" bar (§3.3) -- a tiling
  pipeline would be solving a scale problem this neighborhood doesn't
  have yet. Revisit if/when Phase 15 generalizes to a larger second city.

## Amendment (2026-09-08, Phase 8): the SSE idle-timeout check had a real bug

Building Phase 8's frontend (the actual `fetch`-based SSE client,
`apps/web/lib/sse.ts`) surfaced a bug in decision 4's live-wait loop that
every Phase 7 test missed, because they all exercised `replay_events_after`
directly against an *already-finished* job -- pure replay, never the
live-wait branch.

**The bug**: `redis.asyncio`'s `pubsub.get_message(timeout=N)` does not
reliably block for the full `N` seconds. Its *first* call right after
`subscribe()` consumes the subscribe-confirmation control message Redis
sends immediately; because the endpoint passes `ignore_subscribe_messages=True`,
that message is filtered out and the call returns `None` almost
instantly rather than continuing to wait out the remaining timeout budget
for an actual data message. The original code treated any single `None`
as "nothing will ever arrive" and closed the stream -- meaning a client
that connected before the solve had even started (a fast client racing a
job whose replay list is still empty) had its connection closed within
milliseconds, before the worker ever published anything. Manual `curl`
verification during Phase 7 never caught this because curl's own
process-spawn latency usually let at least one event land in the replay
list first, masking the live-wait branch entirely.

**The fix**: poll `get_message()` in short (`SSE_POLL_INTERVAL_SECONDS =
1.0`) increments inside the same loop, re-checking `is_disconnected()`
every poll, and only actually give up once that many *consecutive* short
polls -- not one single long `timeout=` call -- have come back empty
(tracked via `idle_seconds` against `SSE_IDLE_TIMEOUT_SECONDS`).

Caught and pinned down with a regression test
(`apps/api/tests/test_solve_end_to_end.py::test_sse_endpoint_does_not_close_before_the_worker_publishes_anything`)
that opens the real HTTP endpoint via `httpx.ASGITransport` and starts
reading *concurrently* with the solve job (`asyncio.gather`), not
sequentially after it -- confirmed to fail against the pre-fix code and
pass against the fix.
