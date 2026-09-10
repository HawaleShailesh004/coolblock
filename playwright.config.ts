import { defineConfig, devices } from "@playwright/test";

/**
 * Phase 13's E2E suite (COOLBLOCK-BUILD-PLAN.md: "the full journey, the
 * share flow, the export flow, the reconnect flow"). The reconnect flow
 * is covered at the API level instead
 * (apps/api/tests/test_solve_end_to_end.py already exercises the SSE
 * replay-after-disconnect contract directly against Redis/Postgres) --
 * duplicating that as a flaky browser-level network-throttle test would
 * be a weaker version of a check that already exists and is stronger
 * where it is.
 *
 * Requires the real stack running (docs/RUNNING-AND-TESTING.md's own
 * multi-terminal setup: Docker infra, `uv run uvicorn ...`, `uv run
 * arq ...`, `pnpm --filter @coolblock/web dev`) -- not auto-started here.
 * A real solve needs the cached candidate export
 * (data/derived/edison-eastlake/candidates.geojson) and a real ARQ
 * worker; there is no lightweight fake to substitute for either without
 * testing something other than the real app.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // shares one real Postgres database; sequential avoids one test's plan rows confusing another's
  // `fullyParallel: false` alone still lets Playwright run different spec
  // *files* concurrently across workers -- a real problem hit running
  // this suite: multiple browser contexts kicking off real solves at once
  // against the one ARQ worker process this project runs (docs/RUNNING-AND-TESTING.md's
  // single `uv run arq ...`) queued up and blew past the 30s completion
  // budget below, timing out tests that would otherwise pass. `workers: 1`
  // makes every test in the suite genuinely sequential, matching the one
  // real (not horizontally-scaled) backend it runs against.
  workers: 1,
  retries: 0,
  timeout: 60_000,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3001",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
