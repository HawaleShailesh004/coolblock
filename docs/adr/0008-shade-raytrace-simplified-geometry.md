# 8. Shade raytracing: real solar geometry without a full height-field sweep

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §6.3 C2 specifies, for the design day (the
hottest historical day) at hourly steps 09:00-18:00: solar azimuth/
elevation from `pvlib`; a height field of DEM + building heights +
existing canopy + proposed canopy; GPU-style horizon-angle-sweep shadow
casting on that height raster; intersection with pedestrian surfaces; and
shade-hours delivered per candidate as the output metric.

A full raster horizon sweep over the whole neighborhood for every hour of
the design day, accounting for every building and every existing/proposed
canopy element occluding every other, is a substantially larger undertaking
than the other Phase 5 modules (C1, D1, D2) -- effectively a mini
raytracer -- and the ingested DEM (D12) has no matching nDSM to give real
canopy or building *heights* above bare earth beyond OSM's building-height
tags already used by `engine/surface/heights.py`.

## Decision

Implement C2 with real solar geometry and real pedestrian-surface data,
but a deliberately simplified shadow model:

1. **Per-candidate direct shadow, not a full-scene z-buffer.** Each
   candidate's own shadow (a rectangle: assumed height/tan(elevation)
   long, capped at 60m, assumed crown/structure width wide, pointing away
   from the sun) is intersected against real pedestrian-surface vector
   data (OSM footways/steps/pedestrian, bus stops, playgrounds, school
   grounds). Whether an intervening building would already shade or block
   that path first is not modeled.
2. **Design day is real, not assumed** -- the actual hottest day in the
   ingested Open-Meteo 2021-2025 summer series (2025-07-09, 46.9°C),
   found by `find_design_day()` rather than picked by hand.
3. **`shade_structure` candidates are scored by C2 with their own assumed
   dimensions** (3m tall, 3m wide), unlike C1 which explicitly excludes
   them (`docs/adr/0007-*.md`). The split is deliberate, not an oversight:
   C1 models ambient, evapotranspiration/albedo-driven cooling that only
   living canopy provides; C2 models direct shading, which both a tree
   canopy and a physical structure provide identically by blocking solar
   radiation. This is where a shade structure's real cooling benefit is
   captured.
4. **School routes are approximated by school grounds.** No walking-route
   relations exist in this bbox's OSM extract, so buffered `amenity=school`
   footprints stand in for the plan's "school walking routes" -- narrower
   in scope, disclosed as such.

## Consequences

- Shade-hours results reflect real geographic siting (street trees, sited
  near roads by `engine/surface/candidates.py`'s own logic, measurably
  outperform park-lot clusters sited in interior lots) but do not account
  for a tall building already shading a candidate's location for part of
  the day -- such a candidate's *measured* shade-hours here could be an
  overcount relative to a full occlusion-aware model (the candidate's
  pedestrian-surface target might already be shaded by something else,
  making the candidate's own contribution smaller in reality than modeled).
- A future full raster sweep (§6.3 C2's literal spec) is a natural upgrade:
  the DEM (D12) and building heights (`engine/surface/heights.py`) it
  would need are both already ingested and available, so the gap is
  implementation effort, not missing data.
- Any UI or report copy citing shade-hours must state the design day
  (2025-07-09) and note that the metric is each candidate's own modeled
  shadow reach, not a scene-wide raytrace result.
