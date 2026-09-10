# 26. Phase 12: a real marketing homepage, and real web fonts

Date: 2026-09-10

## Status

Accepted

## Context

`apps/web/app/page.tsx` was still the literal Phase 0 foundation-commit
placeholder ("COOLBLOCK · PHASE 0 · FOUNDATIONS"), unrevisited through
Phases 1-13. §9.7's full spec is a scroll-driven React Three Fiber hero
(a stylized 3D block that heats up scrolling into the problem and cools
scrolling into the solution) -- a substantial, novel piece of engineering
this pass did not build, given the remaining time before the plan's own
Day 7 feature-freeze checkpoint and the value of shipping a real,
honest, working page today over an unfinished, unverified 3D one.

## Decision

A real, static-generated one-pager, built with the same "Field
Instrument" light/editorial marketing tokens (§8.1, `packages/ui/src/tokens.css`)
the app already declares but never applied:

- **Hero**: the plan's own established headline ("Where should the next
  40 trees go?"), the real §2.2 friction framing, and a hero image that
  is a genuine screenshot of the live product (`apps/web/public/hero-map.png`,
  captured via a Playwright script against the running app after
  `docs/adr/0025-*.md`'s building-opacity fix) -- not a mockup.
- **Stats strip**: four numbers, all real and already computed elsewhere
  in this project -- the 4.6-14x baseline uplift (`docs/METHODOLOGY.md`),
  2,844 buildings and 4,371 candidate sites (the same counts the app's
  own left rail displays), and the 5 real cited papers.
- **The core loop** (§2.3), the five real citations with real DOI links
  (`data/cache/literature/*/citations.json`), and an honest disclosure
  section restating the honesty rail (heat surface: 2 of 3 validation
  checks) -- no fabricated claim anywhere on the page.

**A second real gap found and fixed while building this**: `tokens.css`
itself already said *"Faces are loaded where used (apps/web)"* --
but nothing ever loaded them. `--font-display`/`--font-ui`/`--font-mono`
were plain font-family fallback stacks naming fonts
(`"Instrument Serif"`, `"Inter Variable"`, `"JetBrains Mono"`) that are
not pre-installed on essentially any visitor's machine, so every page in
this app -- including the running product at `/map` -- has been silently
rendering in Georgia/system-ui/monospace fallbacks this entire build,
not the specified faces. Fixed in `apps/web/app/layout.tsx` via
`next/font/google` (Fraunces, Inter, JetBrains Mono), each configured
with `variable` set to the exact same custom-property name `tokens.css`
already uses, so the override is transparent to every existing
component. `next/font` self-hosts the downloaded files and serves them
from this app's own origin -- no runtime fetch to Google's CDN, so
`docs/adr/0023-*.md`'s CSP needed no new exception. Confirmed with a
real screenshot: the hero headline renders in an actual serif display
face, not a fallback.

## Consequences

- No git remote is configured for this repository yet (`git remote -v`
  returns nothing), so the page does not link to a GitHub URL that would
  otherwise be guessed or fabricated -- the methodology disclosure is
  prose, not a dead or invented link.
- Production build: `/` is static-generated, 5.38 kB page weight, 114 kB
  First Load JS -- comfortably inside §9.7's LCP < 1.8s target, with no
  3D/WebGL bundle weight since the R3F hero wasn't built.
- The full §9.7 spec (the scroll-driven heating/cooling 3D hero, the
  live demo embed, an in-app methodology page per Phase 14) remains
  open, disclosed here rather than implied done.
