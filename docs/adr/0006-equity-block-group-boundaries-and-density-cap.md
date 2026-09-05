# 6. Equity: added D7b block-group boundaries, capped population density

Date: 2026-09-05

## Status

Accepted

## Context

Phase 5's dasymetric population redistribution (D1, COOLBLOCK-BUILD-PLAN.md
§6.4) needs a real block-group *polygon* set to spatially join residential
building footprints (D4/OSM) against, so each building can be attributed to
a block group and given a share of that block group's ACS population (D7).

The only block-group polygon set already cached at the start of Phase 5 was
D10 (Tree Equity Score, 2020 vintage). It matched only 9 of D7's 23
ACS5 block-group GEOIDs -- the Census Bureau periodically redraws
block-group boundaries between decennial cycles, and TES and ACS5 don't
share a vintage here. Proceeding with D10's boundaries would have silently
dropped 14 of 23 block groups' population from the redistribution.

Separately, once redistribution was working end to end, a real building in
a university/stadium block group near Chase Field (30 buildings, mostly
`university`/`stadium`/`roof` tagged, only 1 left classified residential
after fixing two `building=yes` misclassifications -- see
`engine/equity/population.py`'s module docstring) was absorbing its
block group's *entire* ACS population: 2,061 people onto a single-storey,
370 m² footprint. Physically impossible, and not a boundary-clipping
artifact (the block group was confirmed 99.99% inside the study bbox).

## Decision

1. **Added D7b** (`engine/ingest/d07b_tiger_bg.py`): Census TIGER/Line 2022
   block-group boundaries, fetched directly (keyless REST), clipped to the
   same locked bbox as every other source. Not one of the original 16
   data-contract sources -- an addition driven by a real join requirement
   Phase 5 uncovered. Matches 18 of D7's 23 block groups (the remaining 5
   legitimately don't overlap the study bbox).
2. **Capped per-building density** at `MAX_PERSONS_PER_M2_FLOOR_AREA` (1
   person per 15 m² of footprint × floor-count -- a dense-apartment rate)
   in `redistribute_population()`. Population a block group's identified
   buildings can't plausibly hold under that cap is not dropped or
   silently redistributed elsewhere -- it's tracked explicitly per block
   group by `summarize_unallocated_population()`.

## Consequences

- Population totals from `redistribute_population()` will not sum to each
  block group's full ACS population wherever the cap binds. Any downstream
  consumer (equity scoring, UI totals) must use the capped `population`
  column as "plausibly located" people, and consult
  `summarize_unallocated_population()` if it needs the true ACS total.
- Measured on real data: of 25,953 total ACS population across all 23
  block groups (18 of which have D7b boundary matches), 13,253 (~51%) is
  plausibly allocated to specific buildings; the remainder is disclosed as
  unallocated rather than overstated. This is a genuine finding about OSM
  residential-building under-coverage in Edison-Eastlake, not a modeling
  shortfall to be hidden -- it should be stated as-is in any UI or report
  copy that surfaces per-building or per-block-group population.
- D7b joins the data-source manifest and version-directory caching pattern
  identically to the original 16 sources, so it participates in
  `engine/ingest/run_all.py` and the same idempotent re-fetch behavior.
