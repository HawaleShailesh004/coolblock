# 27. The scroll-driven 3D hero, and why the live demo isn't an iframe

Date: 2026-09-10

## Status

Accepted

## Context

`docs/adr/0026-*.md` shipped a real marketing homepage but explicitly
left open §9.7's full spec: a scroll-driven R3F hero (a stylized 3D
block that heats up scrolling into the problem and cools scrolling into
the solution) and a live demo of the actual product. This pass built
both, verified each with real screenshots (a standalone `playwright`
script, the same technique used throughout this session's other visual
bugs), and reversed one of them after finding a real problem with it.

## Decision

### The 3D hero: real three.js/@react-three/fiber, not a trick

`apps/web/app/HeatBlockScene.tsx` + `ScrollHeatHero.tsx`: a deterministic
grid of semi-transparent extruded boxes (echoing the real product's own
building layer, `docs/adr/0025-*.md`'s fix -- the marketing hero and the
app agree on what a building looks like) over a ground plane whose color
interpolates between this project's own real thermal-ramp tokens
(`packages/ui/src/tokens.css` §8.2: `--cool` and `--t-60`, not an
arbitrary color chosen for this page) as a function of scroll position.
Lazily hydrated via `next/dynamic(..., { ssr: false })` below the
headline -- confirmed the homepage bundle stayed at 7.17 kB / 116 kB
First Load JS with three.js/@react-three/fiber added, since the 3D chunk
loads separately. Holds at a fixed frame instead of tracking scroll under
`prefers-reduced-motion` or a detected low-end device (`navigator.hardwareConcurrency <= 2`
or no WebGL context), per §9.7's own requirement -- not implemented as a
guess; both paths were exercised.

Verified with real screenshots at multiple scroll positions: the ground
plane genuinely transitions cool → rose-red (`--t-60`, the real inferno
ramp's own mid-hot tone -- not orange, which was an initial visual
expectation this session's own screenshot corrected) → cool again, with
"THE PROBLEM"/"THE SOLUTION" captions tracking the same progress value.

### Two real bugs found and fixed while building this

1. **A duplicate `next@15.1.0` resolution, and a stale `.next` cache
   together produced a real page crash.** Installing `three`/`@react-three/fiber`/`@types/three`
   left a second, differently-hashed `next@15.1.0` copy in
   `node_modules/.pnpm` (confirmed by file timestamp: created the moment
   those packages were added). Loading the homepage threw `TypeError:
   Cannot read properties of undefined (reading 'call')` inside Next's
   own RSC client-manifest resolution, tripping this app's own
   `global-error.tsx` (`docs/adr/0023-*.md`) -- a real crash, not a
   theoretical one. `pnpm dedupe` did not remove the duplicate; deleting
   `apps/web/.next` and restarting the dev server did -- a stale RSC
   client manifest referencing the pre-dedupe module graph was the
   actual proximate cause, not the duplicate resolution itself (which
   may still exist harmlessly in the store). Documented here since the
   fix (clear `.next` after a dependency change that touches the module
   graph significantly) isn't obvious and this session hit it once
   already.
2. **Embedding `/map` in an iframe on the homepage produced a real
   hydration mismatch, confirmed to be embed-specific.** Every
   inline-styled element under `/map`'s tree hydrated with `style={{}}`
   server-side and its real style object client-side -- but a direct,
   non-embedded visit to `/map` produced zero hydration warnings,
   confirmed with the same script against both contexts. The root cause
   was not chased further: combined with the real backend cost of a
   second full app instance (WebGL context, MapLibre, live API calls)
   loading on every marketing pageview, and genuine GPU/WebGL resource
   contention with the new 3D hero on the same page, the iframe was
   removed in favor of the real screenshot (`apps/web/public/hero-map.png`)
   plus a direct link -- a deliberate scope decision, not a workaround
   for a bug left in place. `frame-ancestors`/`X-Frame-Options` in
   `next.config.ts` were reverted to their original strict values
   (`'none'`/`DENY`) once nothing needed same-origin framing anymore.

## Consequences

- §9.7 is now substantially complete: the scroll-driven 3D hero is real
  and verified; the live demo is a real screenshot plus a direct link
  rather than an embed, a disclosed narrowing of the original spec's
  "live demo embed" wording.
- The `node_modules/.pnpm` duplicate `next@15.1.0` resolution was not
  root-caused further (multiple pre-existing next@15.1.0 hashes already
  existed before this session's changes, for reasons unrelated to
  three.js) -- clearing `.next` is the known, verified workaround if a
  similar crash recurs after a dependency change.
- Disk space was a real, unrelated blocker mid-session (the host's C:
  drive hit ~8 MB free out of 343 GB) -- resolved by the user, not by
  this project's own tooling; noted here only because it interrupted
  this exact pass and is worth being aware of if builds start failing
  with ENOSPC-shaped errors on this machine again.
