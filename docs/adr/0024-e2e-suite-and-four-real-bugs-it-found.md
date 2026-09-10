# 24. A real Playwright E2E suite, and four real bugs it found

Date: 2026-09-08

## Status

Accepted

## Context

Phase 13's own DoD: *"E2E (Playwright): the full journey, the share
flow, the export flow, the reconnect flow."* `playwright` (the driver
library) was already a pre-provisioned devDependency, but no
`@playwright/test` (the actual test runner), no config, and no tests
existed. The reconnect flow is covered separately and already exists:
`apps/api/tests/test_solve_end_to_end.py` exercises the real SSE
replay-after-disconnect contract directly against Redis/Postgres --
duplicating that as a browser-level network-throttle test would be a
weaker version of a check that already exists and is stronger where it
is, so this pass built the other three: the full journey, the share
flow, the export flow.

Writing tests that actually drive the real app in a real browser against
the real backend -- rather than only reading the code -- surfaced four
real, independent bugs, none of which were hypothetical: every one was
confirmed by actually reproducing the failure (a Playwright test error,
a direct `curl` comparison, or a live console-error capture), not
inferred from reading source.

## Decision

### Infrastructure

Added `@playwright/test` (the `playwright` package installed earlier was
only the driver library), `playwright.config.ts` (root), `e2e/*.spec.ts`,
and a root `tsconfig.json` + `@types/node` so the suite typechecks (it
sits outside the pnpm workspace's `apps/*`/`packages/*` glob, so it isn't
covered by `turbo run typecheck`/`lint` automatically -- wired into the
root `package.json`'s `typecheck`/`lint`/new `e2e` scripts instead).
`workers: 1` is load-bearing, not a style choice: `fullyParallel: false`
alone still let different spec *files* run concurrently across workers,
and several tests running real solves at once against the one ARQ worker
process this project runs caused real timeouts -- fixed by making the
whole suite genuinely sequential, matching the one real (not
horizontally-scaled) backend it exercises.

### Bug 1 -- the share page never existed

`OptimizerPanel`'s "Share link" button generated a URL pointing at
`/share/[token]`, and the backend's `GET /share/{token}`
(`apps/api/src/coolblock_api/routers/share.py`) was already built and
required no auth by design -- but no `/share/[token]` page existed in
`apps/web/app/`. Clicking the button worked; visiting the link it
produced did nothing. Built the missing page: a read-only view fetching
`GET /share/{token}` and rendering the scenario's summary and ranked
sites table. A generated OG image for link previews (§9.7) remains a
disclosed gap, not built here.

### Bug 2 -- the export links silently 404'd

`Export GeoJSON`/`Export CSV` were plain `<a href>` links to a
workspace-scoped endpoint (`get_current_workspace`) -- but a browser's
plain link navigation carries no custom headers, so the backend's
dev-auth fallback resolved `x-dev-workspace-id`'s *default*
(`"dev-workspace"`), not this app's actual `"demo-workspace"`
(`apps/web/lib/api.ts`'s `authHeaders()`). Confirmed directly: the same
URL returned `200` with the right headers and a real `404 "scenario
version not found"` with none, against a real plan that genuinely
existed. Fixed correctly, not worked around: `downloadScenarioExport()`
fetches with `authHeaders()` and triggers a client-side `Blob` download,
the same fix any authenticated download needs when a browser's own
navigation can't carry the required headers.

### Bug 3 -- CORS only ever allowed port 3000

`Settings.cors_allow_origins` defaulted to exactly
`["http://localhost:3000"]`. Next.js silently falls back to 3001, 3002,
... when 3000 is already taken -- which it was, on this very machine,
mid-session, by an unrelated project's own dev server, entirely outside
this project's control. With only 3000 allowed, every browser fetch from
the actual running dev server failed as an opaque CORS error; the
optimizer never even started (no "creating" state, no error message --
`createPlan()`'s fetch simply never resolved as the browser saw it).
Since a judge's machine is exactly the kind of environment where port
3000 might already be occupied by something else, this was a real
demo-day risk, not a local-machine curiosity. Widened the default to the
handful of ports Next actually tries (3000-3002) -- still a real, closed
allowlist, not `"*"` -- overridable via `CORS_ALLOW_ORIGINS` in `.env`.

### Bug 4 -- the previous pass's own CSP broke the optimizer in dev mode

The most consequential finding, and a direct callback to `docs/adr/0023-*.md`'s
own disclosed limitation ("whether the map's actual WebGL rendering is
CSP-clean needs a real browser check"). With a browser now available
(Playwright), the answer was concrete: `script-src 'self' 'unsafe-inline'`
(no `'unsafe-eval'`) threw `Evaluating a string as JavaScript violates
... 'unsafe-eval' is not an allowed source` the instant "Run optimizer"
was clicked in `next dev` -- the single most important feature in the
product, silently dead on the exact mode `scripts/dev.sh` runs the demo
in. A real production build (`next build && next start`) completed the
identical real solve with the identical strict `script-src` and no error
at all -- proving this is Next's own dev-mode webpack tooling
(HMR/eval-source-map) needing `eval`, not this app's code or its
dependencies (React, maplibre-gl, deck.gl). Fixed by gating
`'unsafe-eval'` to `process.env.NODE_ENV !== "production"` in
`next.config.ts` -- development gets the looser policy Next's own
tooling requires, production keeps the strict one, and this asymmetry is
the point, not an oversight.

## Consequences

- All three E2E specs pass against the real, full local stack (Docker
  infra, a real `uv run uvicorn`/`uv run arq`, a real `next dev`) --
  6/6 tests green, none skipped, none mocked.
- `docs/RUNNING-AND-TESTING.md` gains the E2E suite's own prerequisites
  and run command, matching every other "how to actually verify this"
  section in that document.
- The reconnect flow's coverage lives at the API level
  (`test_solve_end_to_end.py`), not duplicated here -- a deliberate scope
  choice, not an oversight, recorded so a future reader doesn't go
  looking for a fourth spec file that was never meant to exist.
- Bug 4 in particular is a reminder specific to this build's own
  practice this session: a change verified only by `curl`/build/typecheck
  (real verification, but partial) can still hide a defect that only a
  real browser click surfaces -- worth remembering the next time a
  frontend change ships without one available.
