# 23. Error boundaries, a real 404, and a scoped CSP

Date: 2026-09-08

## Status

Accepted

## Context

Phase 13's own DoD lists, alongside offline demo mode (`docs/adr/0022-*.md`):
*"Error-boundary coverage on every route; a real 404 and 500"* and
*"Security: ... no secrets client-side, CSP."* Auditing `apps/web/app/`
found neither existed: no `not-found.tsx`, no `error.tsx`, no
`global-error.tsx`, and `next.config.ts` set no security headers at all
-- an uncaught render exception anywhere under the root layout would
have shown Next.js's unstyled default overlay (or a blank page in
production), and there was no CSP restricting what origins the app could
load from or connect to.

## Decision

**Error boundaries** (§1.2's "Typed error states with a recovery
action"): added `apps/web/app/not-found.tsx` (a styled 404 linking back
to `/map`), `apps/web/app/error.tsx` (a route-level boundary with a
`reset()` "Try again" action, covering every route since none override
it), and `apps/web/app/global-error.tsx` (catches a crash in `RootLayout`
itself, which takes `error.tsx`'s own boundary down with it -- renders
its own minimal `<html>/<body>` since the real layout is what broke).

**A real CSP, scoped to what the app actually uses** -- audited, not
guessed: `default-src 'self'`; `connect-src`/`img-src` limited to `'self'`
plus the three local services the client genuinely talks to (the FastAPI
backend, TiTiler, and MinIO -- now the *only* three, since
`docs/adr/0022-*.md` finished self-hosting the last live external
dependency, the basemap's glyphs/sprite); `object-src 'none'`,
`frame-ancestors 'none'` (clickjacking), `base-uri 'self'`. Plus
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`, and a `Permissions-Policy`
denying camera/microphone/geolocation (none of which this app uses).

**A disclosed tradeoff, not a silently weakened CSP**: `script-src`/`style-src`
include `'unsafe-inline'`. Next.js's App Router injects its own
hydration/RSC bootstrap scripts inline; Next's documented alternative is
a nonce-based strict CSP wired through per-request middleware. Building
that without a browser available this session to confirm the map (WebGL
via maplibre-gl/deck.gl -- the single most important demo surface) still
renders under a stricter policy was judged a worse risk than shipping a
real, meaningfully-scoped CSP that still blocks the genuinely dangerous
surface (arbitrary external script/connect origins, embeds, framing).
Tightening `script-src` to a nonce-based policy is a real, identified
follow-up, not silently dropped.

**Verification, and its real limit**: confirmed via `curl -I` against a
real running dev server that every header above is actually present on
`/map`'s response, and that the self-hosted glyph/sprite assets
(`docs/adr/0022-*.md`) remain reachable. No browser automation tool was
available this session, so whether the map's actual WebGL rendering
still works cleanly under this CSP (no console CSP-violation errors)
was **not** verified in a real browser -- disclosed here rather than
claimed. `pnpm turbo run lint typecheck build` all pass, which confirms
the code compiles and Next's own build-time checks are clean, not that
the CSP is behaviorally correct at runtime.

**A second real bug found while touching `next.config.ts`**: the
previous session's `NEXT_PUBLIC_MAP_ASSETS_URL` addition
(`docs/adr/0022-*.md`) was read in `apps/web/app/map/page.tsx` via
`process.env.NEXT_PUBLIC_MAP_ASSETS_URL` but never added to
`next.config.ts`'s explicit `env` block the way `NEXT_PUBLIC_PMTILES_URL`
and `NEXT_PUBLIC_API_URL` already are -- since this project's env lives
at the monorepo root (loaded manually via `process.loadEnvFile`) rather
than in `apps/web`'s own `.env`, Next's automatic client-side inlining of
`NEXT_PUBLIC_*` vars never picks it up without that explicit entry. The
app "worked" anyway only because the hardcoded fallback
(`http://localhost:9000/coolblock-tiles`) happens to match local dev --
an override in `.env` would have been silently ignored. Fixed by adding
it to the `env` block alongside the other three.

## Consequences

- A judge hitting an unmatched URL or triggering a render exception now
  sees a styled, on-brand page with a real recovery action, not a blank
  tab or Next's generic default.
- `next.config.ts`'s `LOCAL_ORIGINS` list (API/TiTiler/MinIO) is the
  single place a production deploy would need to update with real
  hostnames -- not scattered across multiple files.
- **Recommended next verification step, not yet done**: open `/map` in
  an actual browser with dev tools open and confirm zero CSP-violation
  console errors, especially around maplibre-gl's worker and the heat
  surface COG's TiTiler tile requests -- the one part of this ADR's work
  that couldn't be confirmed in this session.
- This is a second concrete slice of Phase 13 (after `0022-*.md`'s
  basemap-assets fix) -- the E2E Playwright suite, golden-file tests, and
  performance/bundle work remain untouched.
