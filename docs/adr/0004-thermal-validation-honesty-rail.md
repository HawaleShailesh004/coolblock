# 4. Thermal surface validation gate: honesty-rail language downgrade

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §1.4 requires that if the A3 validation gate
(§6.1 A3) does not confirm the thermal surface, the product's language
downgrades from "predicted cooling" to "prioritization score" everywhere,
recorded in the same commit as the code that made the call. §6.1 A3
specifies three independent checks: station correlation, land-cover
thermal contrast, and agreement with city-published hot spots.

`engine/thermal/validate.py` implements all three against real Phase 1
data for Edison-Eastlake. Full numbers: `docs/METHODOLOGY.md` and
`notebooks/01-thermal-validation.ipynb`.

## Decision

The gate did not clear: 2 of 3 checks pass (station correlation r=0.369;
city hot-spot rank agreement against Phoenix's own 2024 Shade Plan,
ρ=0.683). The land-cover contrast check fails with the wrong sign
(parking reads 13.2°C *cooler* than grass), traced to the available OSM
`amenity=parking` polygons being multi-storey structures (rooftop
temperature) rather than open asphalt lots, and to no clean "cool,
irrigated park" ground-truth polygon existing in this neighborhood's OSM
tags either way.

Per §1.4, a 2-of-3 result is not a pass. **Every UI surface, generated
memo, and API field that presents the heat surface's output must use
"prioritization score" language, not "predicted cooling" or "modeled
temperature reduction," until check #2 is re-run against better ground
truth and passes.**

## Consequences

- Phase 5 (impact/equity) and Phase 6 (optimizer) objective descriptions
  must use "prioritization score," not degrees of predicted cooling, in
  any user-facing copy, until this ADR is superseded.
- Phase 10's narrate module (Claude-generated memo/rationale copy) must be
  prompted consistently with this language, not independently worded.
- Follow-up to actually clear the gate: re-run check #2 using Maricopa
  County parcel land-use codes (D6, `LC_CUR` field) to identify genuine
  open-lot/parking parcels and irrigated park parcels, instead of OSM
  `amenity`/`landuse` tags. Tracked as Phase 5+ work, not blocking Phase 4.
- The R²=0.215 / RMSE=0.94°C downscaling metrics and the uncertainty
  raster are reported regardless of the gate's outcome (DoD requirement,
  independent of the honesty-rail language decision).
