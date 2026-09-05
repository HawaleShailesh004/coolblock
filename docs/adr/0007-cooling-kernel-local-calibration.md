# 7. Cooling kernel: locally calibrated beta, no wind term, shade structures excluded

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §6.3 C1 specifies:

    ΔT_peak = β · f_canopy_increment · g(impervious_fraction) · h(LST_anomaly) · w(wind/aspect)
    ΔT(d)   = ΔT_peak · exp(−d² / 2σ²)        σ ≈ 25-40 m

with β "calibrated ... by fitting observed LST against observed canopy
across the neighborhood -- i.e. calibrated on the target city's own data,
not imported wholesale," and every coefficient "stored with its source and
its confidence interval."

Three real decisions came up implementing this against Edison-Eastlake's
actual ingested data:

1. There is no wind-direction or urban-canyon airflow model anywhere in
   this project's data contract or scope. Open-Meteo (D13) gives a single
   neighborhood-average wind speed/direction for the design day, which
   cannot resolve street-canyon channelling at the scale of an individual
   candidate (a single block face vs. another).
2. Once the kernel was implemented and run against Phase 4's real 1,472
   candidates, `shade_structure` candidates (bus-stop shade structures,
   not trees) received nonzero ΔT_peak values from the tree-crown-area
   formula -- a real bug caught by inspecting the per-intervention-type
   output, not a theoretical concern: shade structures don't plant canopy,
   so `f_canopy_increment` is undefined for them, not just small.
3. The regression's R² came back at 0.073 -- canopy fraction, even
   controlling for impervious %, explains a small share of raw LST
   variance in this neighborhood (LST is driven by many factors: albedo,
   building mass, irrigation, proximity to bare desert soil).

## Decision

1. **w(wind/aspect) is omitted, held at 1.0.** Not estimated, not faked
   from the single averaged Open-Meteo wind reading -- disclosed in the
   module docstring and `docs/METHODOLOGY.md` as a real gap versus the
   plan's literal formula, not silently dropped.
2. **`shade_structure` candidates get `delta_t_peak_degc = 0.0` from C1**,
   explicitly excluded via `CANOPY_INTERVENTION_TYPES` rather than passed
   through the tree formula. Their cooling benefit is deferred to C2
   (shade-hours delivered to pedestrian space) when implemented -- a
   different physical mechanism (direct shading) from ambient
   canopy-driven cooling, and conflating the two would have been worse
   than declining to score them here.
3. **β's low R² is reported alongside the coefficient itself**, not
   dropped from the output or buried. `CoolingKernelCalibration` carries
   `r2` and `n_pixels` so any downstream consumer (the optimizer's
   objective, a UI tooltip) can show both "how much cooling, per this
   fitted relationship" and "how well that relationship explains the
   neighborhood's actual temperature pattern."

## Consequences

- `run_cooling_kernel()`'s output is only meaningful for `street_tree` and
  `park_lot_tree_cluster` candidates; any candidate scoring or optimizer
  code consuming `delta_t_peak_degc` must not treat a shade structure's
  0.0 as "this candidate has no benefit" -- it has an unmeasured-by-C1
  benefit, pending C2.
- Beta's confidence interval is tight (does not cross zero) even though R²
  is low -- these measure different things (precision of the coefficient
  estimate vs. how much of the outcome it explains) and both numbers
  should travel together in any report or UI copy referencing this model,
  per the project's honesty-rail posture (`docs/adr/0004-*.md`).
- If a DSM/nDSM becomes available later (already flagged as absent in
  `docs/adr/0005-*.md`), canopy fraction could be derived from actual
  vegetation height instead of the buffered-OSM-tree-point proxy, likely
  improving R² without changing this ADR's wind/shade-structure decisions.
