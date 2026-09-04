# CoolBlock — Methodology

> Status: Phase 0 skeleton. This page is the honesty rail (COOLBLOCK-BUILD-PLAN.md
> §1.4) rendered in-app — every claim the product makes must trace back to a
> section here. It is not written once at the end; each phase appends its own
> section as that piece of the pipeline lands.

## How to read this document

Every modeled number in CoolBlock carries an epistemic status: computed,
modeled with a stated confidence band, or a prioritization score standing in
for a model that didn't validate. This page is where that status is defined
and where the honesty-rail decisions (§1.4) get recorded when they're made,
not after the fact.

## Sections (filled in as phases land)

- **The heat surface** (Phase 3) — composite method, TsHARP downscaling, the
  A3 validation gate and its result. If validation fails, the language
  downgrade from "predicted cooling" to "prioritization score" is recorded
  here, in the same commit as the code change.
- **Plantable space** (Phase 4) — rule layer vs. ML layer, the fusion rule,
  the manual spot-check error rate.
- **Cooling impact** (Phase 5) — the cooling kernel, its calibration on
  local LST-vs-canopy data, the shade raytrace method, the albedo model and
  its Wolfram unit check (or the fallback noted in `docs/adr/0002-*.md` if
  Wolfram access isn't available yet).
- **Equity weighting** (Phase 5) — the HVI composite, its default weights,
  the sensitivity analysis.
- **The optimizer** (Phase 6) — why this is submodular maximization under a
  knapsack constraint, the three solvers, the measured greedy/exact ratio,
  the baseline comparison and its result.
- **Uncertainty** — how confidence bands are computed and propagated end to
  end, and where they are (and are not) shown in the UI.

See also `docs/LIMITATIONS.md` (Phase 14) for what the product does not
claim.
