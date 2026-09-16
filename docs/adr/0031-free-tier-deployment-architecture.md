# 31. Free-tier deployment architecture: Vercel + Render × 2 + Neon + Upstash

Date: 2026-09-16

## Status

Accepted. Depends on [`0030-*.md`](0030-derived-data-committed-owner-names-stripped.md)
(the derived data this needs is now committed). Step-by-step instructions:
[`docs/DEPLOYMENT.md`](../DEPLOYMENT.md).

## Context

This project's own `.env.example` already named the intended production
shape for object storage ("In production this becomes an R2 bucket +
Cloudflare account credentials") and for the job queue (Redis). Neither
had actually been provisioned or tested end-to-end. Making the deploy
real, not aspirational, required deciding exactly what runs where, on
services with real free-tier limits: Render's free web services have
512MB RAM / 0.1 CPU and sleep after 15 minutes idle (measured backend
peak RSS is 392MB — fits, with little headroom); Render no longer offers
a free managed Redis; Upstash's free Redis is metered per command, not
per hour.

## Decision

**1. Static map assets are served from Vercel, not Cloudflare R2.**
`basemap.pmtiles`, the glyph/sprite files, and the two heat-surface COGs
are small (~4.4 MB total) and already committed
(`apps/web/public/tiles/`, ADR-0030). `packages/map`'s asset-loading code
(`buildBasemapStyle`, `CoolBlockMap`'s `assetsBaseUrl`) already only
assumes an HTTP base URL with `/glyphs/{fontstack}/{range}.pbf` and
`/sprites/black*` beneath it — pointing that base URL at Vercel's own
static hosting instead of a MinIO/R2 bucket needed no code change at all.
This removes an entire external service (and its own account/credential
setup) from the deploy.

**2. TiTiler still runs as a real service (a second free Render web
service), but reads the COG over plain HTTPS, not S3.** `apps/web/app/map/page.tsx`
hardcoded `HEAT_SURFACE_COG_URL` to an `s3://` URL, which only resolves
if the TiTiler process has S3 credentials configured — fine for a Docker
Compose network talking to MinIO, one more credential to provision for a
deployed TiTiler talking to R2. Made configurable
(`NEXT_PUBLIC_HEAT_SURFACE_COG_URL`, added to `next.config.ts`'s env
allowlist — the same silent-override bug ADR-0023 already found once for
`NEXT_PUBLIC_MAP_ASSETS_URL` would otherwise repeat here) and pointed at
the same Vercel-hosted file from decision 1. GDAL's `/vsicurl/` driver
reads any range-request-capable HTTPS URL, no credentials required.

**3. The API and the ARQ worker share one Render service, one Docker
image.** Render's free tier gives one process per service; running two
separate free services here works too, but running them together
(`apps/api/start.sh`, `wait -n` on both process's PIDs so either one
dying takes the container down visibly rather than leaving a half-working
service) uses one fewer of the account's free-tier service slots and
matches exactly how local dev already runs them (`scripts/dev.sh`
docstring's own two-terminal instructions, just combined into one
container instead of two terminals).

**4. Upstash Redis, with ARQ's poll delay tuned up via a new setting.**
`arq`'s own default poll interval (0.5s) issues enough Redis commands
from an otherwise-idle worker to meaningfully eat into Upstash's
metered free tier over a month. `Settings.arq_poll_delay_s` (new,
`ARQ_POLL_DELAY_S` env var) is wired straight into `WorkerSettings.poll_delay`;
recommended production value 5s, trading up to 5 extra seconds of queue
latency (negligible next to the ~2s solve itself, ADR-0028) for a
comfortable command budget.

**5. `ENVIRONMENT` stays non-`production` in this deploy, on purpose.**
No Clerk tenant is provisioned (ADR-0016); `coolblock_api.auth` already
refuses to boot with `environment=production` and no real Clerk
credential, by design, rather than silently running unauthenticated.
This deploy runs the same disclosed dev-fallback auth posture as local
dev (`ENVIRONMENT=staging`) — every visitor shares one fixed workspace.
Not fixed here; disclosed in `docs/DEPLOYMENT.md` as a known limitation,
because building and testing a real Clerk integration is a materially
different piece of work than deploying what already exists.

## Consequences

- Four external services (Neon, two Render services, Upstash) plus
  Vercel — more moving parts than "Vercel + Neon + Render," the
  shorthand this was originally planned under, but an honest reflection
  of the app's real, distinct concerns (database, job queue, tile
  rendering, web app) rather than a deploy that quietly drops one of
  them.
- The TiTiler service is the one piece of this deploy genuinely optional
  to skip for a simpler first pass — every other feature works without
  it; only the live heat-surface map layer doesn't render.
- If a second neighborhood or a real multi-tenant posture is ever added,
  decisions 3 and 5 in particular are worth revisiting — this
  architecture was sized for one locked neighborhood and one shared demo
  workspace.
