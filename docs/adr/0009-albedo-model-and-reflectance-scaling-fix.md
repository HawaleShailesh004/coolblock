# 9. Albedo model: fixed a latent Sentinel-2 scaling bug, new impervious candidates

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §6.3 C3 specifies cool-roof/cool-pavement ΔT via
a surface-energy-balance approximation from albedo change, net radiation
(NASA POWER, D14), and a local convective term, "cross-checked in Wolfram
with real units... because getting W/m² to °C right by hand is exactly
where this kind of model silently breaks." Wolfram access is not available
this session (`docs/adr/0002-*.md`'s documented condition), so the unit
check is done by hand in the module docstring instead of deferred.

C3 needs cool-roof and cool-pavement *candidates* to score, which
`docs/adr/0005-*.md` explicitly deferred out of Phase 4 (they target
impervious surfaces the plantable-space rule layer excludes) and out of
D1's building work (which only classifies *residential* buildings).

While implementing C3, every candidate's modeled ΔT came back exactly
0.0, and every candidate's "current albedo" came back pegged at the
model's clip ceiling (0.9) -- not a plausible physical result. Tracing it
found that `engine/thermal/predictors.py`'s `albedo_proxy` (built in
Phase 3 for the LST downscaling regression) was an unweighted mean of
*raw* Sentinel-2 L2A digital numbers (observed range ~1,450-8,670), not
reflectance scaled to 0-1. This bug existed since Phase 3 but had zero
effect there: `HistGradientBoostingRegressor` splits on relative feature
ordering, which a constant scale factor never changes, so the downscaling
model's fit was identical regardless. It only became visible once the
same value was used as a real physical quantity (Δα in an energy balance)
rather than an opaque regression feature.

## Decision

1. **Fixed the scaling bug at its source** (`engine/thermal/predictors.py`):
   Sentinel-2 bands are now multiplied by the standard ESA 1/10000 scale
   factor before computing `albedo_proxy`. NDVI and NDBI are unaffected
   (band ratios, so a common scale factor cancels). Re-ran the Phase 3
   downscaling and validation test suites after the fix to confirm no
   regression -- both passed unchanged, as expected from a monotonic
   rescaling of one GBM feature.
2. **Added a regression guard**
   (`engine/tests/test_albedo.py::test_albedo_proxy_is_real_reflectance_not_raw_dn`)
   asserting `albedo_proxy` falls in a plausible 0-1 reflectance range,
   so this class of bug cannot silently reappear.
3. **Generated cool-roof and cool-pavement candidates**
   (`engine/surface/impervious_candidates.py`): every OSM building
   footprint (2,842) as a cool-roof candidate, every OSM off-street
   parking lot (57) as a cool-pavement candidate, reusing
   `engine.surface.candidates.classify_ownership` for ownership rather
   than duplicating that logic.
4. **Depaving-to-bioswale remains ungenerated.** No ingested source
   distinguishes pavement that is genuinely excess/removable from
   pavement that is functionally load-bearing (an active parking space,
   an access lane) -- guessing that distinction would be worse than
   omitting the candidate type, consistent with `docs/adr/0005-*.md`'s
   original reasoning for deferring it.

## Consequences

- Any other module reading `engine.thermal.predictors.load_sentinel2_predictors`'s
  `albedo_proxy` for a physical (not purely relative/ML-feature) purpose
  now gets a value in real reflectance units. Any code written *before*
  this fix that assumed raw-DN-scale albedo values (none currently exists
  outside this phase's own new code) would need re-checking.
- C3's ΔT values (mean ≈12.9°C for cool roofs, ≈3.3°C for cool pavement)
  are large relative to C1's tree ΔT_peak (0.1-7.9°C) because they measure
  a fundamentally different quantity -- the retrofit surface's own
  undiluted temperature change at its own footprint, not an
  area-averaged ambient effect. `docs/METHODOLOGY.md` states this
  explicitly; any future D4 (EWCB) implementation combining C1/C2/C3
  contributions into one objective must account for it rather than
  summing the raw ΔT values as if they were the same kind of quantity.
- Cool-roof candidates are generated for every building regardless of
  real roof slope/flatness (no such OSM tag exists here) -- over-inclusive
  versus what a city could realistically retrofit, disclosed in
  `docs/METHODOLOGY.md` rather than silently narrowed by an invented
  heuristic.
