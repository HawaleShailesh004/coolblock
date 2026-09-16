# 32. Every solve was silently touching real names and home addresses

Date: 2026-09-16

## Status

Accepted.

## Context

Testing the deploy image built for `docs/adr/0031-*.md` end to end — not
just building it, actually running a real solve against it, exactly the
"Verify it for real" step `docs/DEPLOYMENT.md` tells everyone else to
do — surfaced a request failing with:

```
FileNotFoundError: /repo/data/cache/maricopa_parcels/2026-09-04/parcels.parquet
```

`engine.optimize.plan_service.stream_solve`'s own docstring states the
warm-solve path "reads the cached, already-scored candidate universe...
instead of recomputing" — true for the *candidates*, but
`build_coverage_objective()` also calls
`engine.impact.ewcb.load_population_points()`, which recomputed D1's
dasymetric population and D2's HVI from **raw ingest cache, on every
single solve request**, with no cache of its own. That reaches
`data/cache/maricopa_parcels/parcels.parquet` — checked directly:

```
OWNER_NAME: 'ALVAREZ TONYA'
PHYSICAL_ADDRESS: '1217 E MCKINLEY ST   PHOENIX  85006'
```

Real people's names, tied directly to their home street address. This is
a materially more sensitive file than the `owner_name`-only column
`docs/adr/0030-*.md` already found and stripped from `candidates.geojson`
— and every solve was reading it, silently, this entire build. Not yet
exposed (this was caught locally, before any deploy target ever ran a
solve against it), but a "run the optimizer" request has no business
touching this file at all, and a deploy target must never be assumed to
have it available regardless.

## Decision

`load_population_points()` (the exact same output for every solve — it
takes no HVI-weight parameter; the live app's HVI weight sliders only
ever recompute the *map choropleth* client-side, never the optimizer's
own objective, confirmed by reading `build_coverage_objective()`'s
signature) now checks for a precomputed cache first
(`data/derived/<neighborhood>/population_scored.geojson`,
`scripts/export_map_layers.py`'s new `export_population_scored()`) and
only falls back to the full raw recompute if that cache is missing —
exactly the same cache-first pattern
`plan_service.load_candidate_universe()` already uses for candidates,
just extended to the one place that didn't have it yet.

`population_scored.geojson` is committed alongside the rest of
`data/derived/edison-eastlake/` (`docs/adr/0030-*.md`'s same narrow
exception) — **column-selected**, matching `export_population()`'s own
existing discipline, not a raw dump of `load_population_points()`'s
output: that output still carries every OSM tag its source
`buildings.parquet` had (`addr:housenumber`, `phone`, `operator`, ...,
almost always null here but real for the odd named business), and
nothing downstream reads any of them back out. Caught by actually
inspecting the first export's first row before committing it — the
first version of this fix would have committed all of that unfiltered.

**Three more raw-cache sources survive this pass, on purpose, added to
the same committed set**: `tiger_block_groups` (constrained solves' zone
assignment), `census_acs5`, and `tree_equity_score` (the baseline
comparison endpoint). All three are aggregate, block-group-level public
government data (Census/USDA Forest Service open data) — checked
directly, not assumed: `census_acs5`'s file is 23 rows, one per block
group, with no field finer than a block-group total. Nothing like
`maricopa_parcels`, which is why that one stays excluded.

## Consequences

- A deployed instance now only needs three small (~80 KB total), public,
  block-group-aggregate cache sources at request time, for two secondary
  features (constrained solves, the baseline chart) — never the raw
  parcel/address data, and never anything for the default unconstrained
  solve at all. The "warm solve" claim `docs/ARCHITECTURE.md` makes is
  now true for the whole default solve, not just the candidate side of
  it.
- Every solve gets measurably faster too (no repeated Census/CDC/parcel
  re-read and re-join), a real side benefit of fixing this properly
  rather than only for the deploy target.
- If HVI weighting is ever wired into the optimizer's own objective
  (currently only a display-side feature), this cache stops being valid
  for anything but the default weights, and `use_cache=False` (or a
  weight-aware cache key) would need to be threaded through from
  wherever the caller's weights come from.
- Re-run `scripts/export_map_layers.py` and commit the result whenever
  D1/D2/D3's computation changes — same discipline as every other
  committed derived file.
