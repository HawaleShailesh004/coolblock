# 34. Split the API and the ARQ worker into two Render services

Date: 2026-09-17

## Status

Accepted. Supersedes decision 3 in
[`0031-free-tier-deployment-architecture.md`](0031-free-tier-deployment-architecture.md)
("the API and the ARQ worker share one Render service").

## Context

The first real production deploy (`docs/adr/0031-*.md`,
`docs/adr/0033-*.md`) went live, and real testing against it — not local
verification, the actual `https://coolblock.onrender.com` — found it
crash-looping: `/health` returned 502, recovered on its own a couple of
minutes later (Render restarting the crashed container), then crashed
again a few minutes after that. A solve triggered right before one of
these crashes sat at `"status":"running"` forever — the worker process
died mid-job, and nothing ever wrote an error state for it, because the
whole container (both processes) had gone down with it.

Measured directly, running each process in its own container against the
same real Postgres/Redis: the API alone uses **~276 MB** RSS, the ARQ
worker alone **~263 MB**. Combined in the one container ADR-0031 chose
(to save a free-tier service slot), that's already **~539 MB at rest** —
over Render free's 512 MB limit before a single request arrives, let
alone a real solve's own peak memory (loading `candidates.geojson`,
`population_scored.geojson`, building the coverage objective, running
HiGHS). ADR-0031's own local verification never caught this: it ran the
container once, hit `/health` and drove one solve through it manually,
which fit — under repeated real traffic on Render's actual (not locally
simulated) memory ceiling, it didn't.

## Decision

`apps/api/start.sh` now reads `$PROCESS_ROLE`:

- `api` — migrations, then the FastAPI server alone.
- `worker` — the ARQ worker alone (no migrations, no port).
- unset / `both` — the original combined behavior, kept only for local
  `docker run` convenience where the 512 MB ceiling doesn't apply.

Same Docker image, same `apps/api/Dockerfile`, two separate Render
services: one `PROCESS_ROLE=api` (with the health check, taking browser
traffic), one `PROCESS_ROLE=worker` (no health check, taking nothing but
Redis jobs). Each fits comfortably under 512 MB on its own.
`docs/DEPLOYMENT.md` rewritten to deploy both from the start (step 3 and
step 4), not offered as an optional split.

## Consequences

- Free-tier service count for this deploy goes from four to five (Neon,
  Upstash, Render × 3, Vercel) — an honest reflection of what it actually
  takes, not a slot saved that cost the deploy its stability.
- A solve that starts right as the worker service restarts (a deploy, a
  free-tier sleep/wake cycle) can still, in principle, be left at
  `"running"` forever if the worker dies mid-job — this decision fixes
  the *cause* found here (memory), not that general class of problem. A
  job-level timeout/reaper wasn't added in this pass; worth doing if a
  stuck-`"running"` scenario is ever seen again after this fix.
- This is the second architecture decision from the deploy work
  (`0031`, `0033`, now `0034`) that a real production failure corrected
  rather than local testing catching first. Local `docker run`
  verification checks that a container *works*; it doesn't check that it
  *survives inside the resource ceiling the real host actually
  enforces* — worth remembering for anything deployed to a
  memory-constrained free tier again.

## Addendum: the worker needs Render's *Background Worker* service type

The first attempt to actually deploy this split, from the user's own
Render dashboard, used **New → Web Service** for the worker (following
this doc's own first draft, which said "a second free service" without
naming the type). It failed:

```
==> No open ports detected, continuing to scan...
==> Port scan timeout reached, no open ports detected. Bind your service
    to at least one port. If you don't need to receive traffic on any
    port, create a background worker instead.
```

`PROCESS_ROLE=worker` deliberately never binds a port — there's no HTTP
traffic for it to serve — but a Render **Web Service** requires one
regardless of what the container actually does, and fails the deploy
after a ~5-minute port scan if nothing ever listens. Render's own error
message names the fix directly: a **Background Worker** is a distinct
Render service type made for exactly this (a long-running process with
no inbound HTTP), and it never runs a port scan at all.

## Second addendum: Background Worker isn't on Render's free tier either

The user tried exactly that, on the real Render dashboard, and reported
back: no Background Worker option is offered on the free plan — only Web
Services. (Not something either this ADR's first addendum or
`docs/DEPLOYMENT.md` had actually confirmed; both assumed Render's own
"create a background worker instead" message meant that path was open
here specifically, rather than checking the free tier's own limits.)

So the worker service stays a **Web Service** after all, and satisfies
Render's port requirement a different way: `PROCESS_ROLE=worker` now also
starts `coolblock_api.worker_stub`, a stdlib-only `http.server` answering
a plain 200 on every path, alongside the real ARQ worker — a few MB, not
the ~270 MB the real API app would cost if used for this instead, which
would have quietly re-created the exact memory problem this whole ADR
exists to fix. `docs/DEPLOYMENT.md` step 4 updated accordingly.
