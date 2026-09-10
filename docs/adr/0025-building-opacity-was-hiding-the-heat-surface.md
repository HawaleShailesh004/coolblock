# 25. Buildings at near-opaque fill were hiding §9 ★1's own "wow"

Date: 2026-09-10

## Status

Accepted

## Context

The user reported the map "looks broken" on the default view. No browser
automation tool being available earlier in this build was flagged as an
open risk (`docs/adr/0023-*.md`, `0024-*.md`) -- this time, a real
screenshot (via a standalone `playwright` script, not an MCP connector)
made the problem directly visible rather than argued about.

The default view (`packages/map/src/viewState.ts`'s `DEFAULT_VIEW_STATE`,
`pitch: 50`) showed almost nothing but near-black background and dark
building silhouettes -- no visible heat-surface color, no visible road
network, nothing resembling `docs/adr/0022-*.md`'s or `docs/METHODOLOGY.md`'s
described product. Investigating layer-by-layer (network capture, then
toggling "Buildings (extruded)" off) showed the actual underlying
rendering was correct the whole time: MinIO/pmtiles/sprite requests all
succeeded, TiTiler served real heat-surface tiles (46/65 requested --
the other 19 were legitimate out-of-bounds boundary tiles at a pyramid
of zoom levels, confirmed directly against TiTiler's own error message,
not a bug), and with buildings hidden the heat surface rendered exactly
as intended: a rich inferno colormap with the real road network visible
through it.

The actual defect: `packages/map/src/layers/buildings.ts`'s
`HEIGHT_PROVENANCE_OPACITY` used near-opaque alpha values (190-255 of
255). `CoolBlockMap.tsx`'s own comment states the intent plainly -- "the
surface glows beneath the 3D block" -- but with ~2,844 densely-packed
buildings rendered at `pitch: 50`, their solid extruded walls (not just
rooftops -- a pitched camera sees building *sides*) visually covered
nearly the entire heat surface underneath. Confirmed by direct
before/after screenshot comparison, not assumed.

## Decision

Halved every tier's opacity (`measured: 255→130`, `levels: 235→115`,
`estimated_default: 190→95`), preserving the honesty-rail's relative
*ordering* (a measured height still renders more solid than an estimated
one) while making every building genuinely semi-transparent. Re-screenshotted
the exact same default view afterward: the heat surface now reads
clearly through the building volumes, with roads visible on top of it --
matching the plan's own described showpiece.

## Consequences

- This was the single highest-value visual fix available: ★1 ("the
  living 3D neighborhood," the plan's own named "45-second wow") was
  being actively undermined by the exact feature meant to make it
  impressive (dense, confident-looking 3D buildings) hiding the exact
  other feature meant to make it impressive (the glowing heat surface).
- No data pipeline, backend, or rendering *code* was broken -- every
  earlier real bug found this session (`docs/adr/0022`-`0024-*.md`) was
  a genuine defect; this one was a design/tuning value that happened to
  regress against its own stated intent as the real building density
  (2,844, not a handful) was reached. Worth remembering: a value tuned
  against a small or synthetic dataset can still be wrong once the real
  one is in place, even with no error anywhere to catch it.
- Confirmed working via direct screenshot comparison (before/after),
  not merely inferred from reading the changed numbers.
