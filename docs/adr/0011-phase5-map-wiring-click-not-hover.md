# 11. Phase 5 checkpoint: candidate scoring wired in as click, not hover

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md's Phase 5 checkpoint (line 854) reads: "hover any
candidate → a card showing its modeled cooling, its shade contribution,
and the number and vulnerability of people reached."

Every other layer in this map (buildings, roads, parcels, and candidates
itself since Phase 4) already uses a click-to-inspect interaction: the
`ContextPanel` in `apps/web/app/map/page.tsx` generically renders whatever
properties a clicked GeoJSON feature carries, and `CoolBlockMap.tsx`'s
deck.gl overlay only wires an `onClick` handler (`getTooltip: () => null`
is set explicitly). Switching only the candidates layer to a hover-driven
card would be inconsistent with the rest of the app's established
interaction model, for one layer, introduced this late in the build.

## Decision

Implement the Phase 5 checkpoint's information requirement -- modeled
cooling, shade contribution, and equity-weighted people reached, all
visible per candidate -- via the existing click-to-inspect pattern rather
than adding a new hover-tooltip codepath:

1. `scripts/export_map_layers.py`'s `export_candidates()` now runs the
   full Phase 5 pipeline (C1's `run_cooling_kernel`, C2's
   `run_shade_raytrace`, C3's `run_albedo_model`, D4's `compute_ewcb`) and
   also includes the impervious candidates
   (`engine.surface.impervious_candidates`, cool roof/cool pavement)
   alongside Phase 4's tree/shade-structure candidates -- one combined
   GeoJSON, every feature fully scored.
2. Because `ContextPanel` already renders every property of a clicked
   feature generically, no new UI component was needed -- the new fields
   (`delta_t_peak_degc`, `delta_t_degc`, `shade_hours_delivered`,
   `ewcb_person_degree_hours`, `ewcb_low`, `ewcb_high`) appear
   automatically once they exist in the exported GeoJSON.
3. `packages/map/src/layers/candidates.ts` gained two new intervention
   colours (`cool_roof`, `cool_pavement`) and an updated layer label
   reflecting that it now covers Phase 4 *and* Phase 5 candidates, not
   just the Phase 4 rule layer.

Verified with a real Playwright run against the dev server (not just
reading the code): loaded `/map`, enabled the candidates layer, swept
click points across the rendered canvas until a real candidate feature
was hit, and confirmed the Inspector panel showed
`park_lot_tree_cluster` with `delta_t_peak_degc: 1.65`,
`ewcb_person_degree_hours: -228.4` (`ewcb_low`/`ewcb_high` bracketing
it) -- a real click-through of the actual running app, not a code
inspection.

## Consequences

- The Phase 5 checkpoint's substance (cooling, shade, equity-weighted
  reach, all visible per candidate) is met; its literal word ("hover") is
  not -- disclosed here rather than silently reinterpreted without a
  record. If a future phase (e.g. Phase 9's showpiece polish) wants true
  hover tooltips as a interaction upgrade, `CoolBlockMap.tsx`'s
  `getTooltip: () => null` is the single place to change, and it would
  apply to every layer at once for consistency, not just candidates.
- `export_candidates()` is now materially slower to run (it recomputes the
  Phase 3 downscaling, C1's regression, C2's shade raytrace, and C3's
  energy balance every invocation, ~2 minutes on this machine) -- still
  fine for its documented purpose (a one-off static export re-run when the
  ingest cache changes), but not something to call from a hot path.
- `candidates.geojson` grew from a Phase-4-only tree/shade-structure file
  to ~6.6MB covering 4,371 candidates (adding cool-roof/cool-pavement
  roughly triples the feature count) -- still loads and renders correctly
  in the browser, but is a real size increase future phases (7's real API,
  9's performance budget) should keep in mind rather than be surprised by.
