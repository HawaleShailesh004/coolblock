# 14. Cool-roof dominance in the unconstrained solve: disclosed, not patched

Date: 2026-09-05

## Status

Accepted

## Context

While testing `engine/optimize/constraints.py` (E3) against the
unconstrained solve for validation, the unconstrained CELF/greedy
solution at a $50,000 budget turned out to select **47 candidates, all
`cool_roof`** -- zero trees. This looked like a bug at first (a maintenance-
cost-cap test showed no effect, which is what surfaced it) and was
investigated rather than assumed correct or dismissed.

The root cause is real and traces back to two already-disclosed decisions:
C1's canopy ΔT (`engine/impact/cooling_kernel.py`) is an area-diluted
ambient effect (a Gaussian kernel spreading one tree's cooling over
~2,827m²), while C3's cool-roof ΔT (`engine/impact/albedo.py`) is the
retrofit's own undiluted surface temperature change at its own footprint
-- `docs/adr/0009-*.md` and `docs/adr/0012-*.md` already state these are
different physical quantities. `engine/optimize/objective.py`'s coverage
function combines both directly into one `max`-coverage sum with no
normalization between them. Cool-roof's ΔT (mean ≈12.9°C) is roughly
40-100x larger than a tree's ΔT_peak (0.1-7.9°C) for comparable per-unit
cost, so it dominates cost-effectiveness at every budget tested.

## Decision

**Disclose this plainly rather than patch it with an invented conversion
factor.** No data ingested in this project supports converting between
"undiluted surface ΔT" and "diluted ambient ΔT" -- doing so would require
a real boundary-layer/convective-mixing model this project does not have.
Fabricating a scaling constant to make the optimizer's output "look more
like a balanced tree-and-roof portfolio" would be worse than reporting
what the model, as honestly built, actually recommends.

`docs/METHODOLOGY.md`'s optimizer section states this finding explicitly,
including two legitimate paths for a future phase to actually resolve it
(a real ambient-equivalent recalibration of C3, or separating surface-
hardening and canopy interventions into distinct objectives/budgets in
the UI) -- neither implemented this phase.

## Consequences

- Any demo, screenshot, or writeup showing an *unconstrained* CoolBlock
  solve at a moderate budget should expect to see cool-roof-heavy results,
  not a mixed tree-and-roof portfolio -- this is not a data or ingest
  problem, and re-running the pipeline will not change it.
- `engine/optimize/constraints.py`'s `public_land_only` and
  `max_sites_per_zone` constraints happen to produce more visually
  "mixed" portfolios in testing (`docs/METHODOLOGY.md`'s E3 section) --
  not because they correct the underlying ΔT-comparability issue, but
  because they remove some of the highest-cost-effectiveness cool-roof
  candidates from eligibility (e.g., private-land buildings). This is a
  side effect of those constraints, not a fix, and should not be
  presented as one.
- If a future phase adds the ambient-equivalent recalibration for C3,
  `engine/optimize/objective.py`'s `_cool_roof_influence` is the function
  to change -- the rest of the coverage/CELF/exact/local-search/baseline
  machinery needs no structural change, since it operates on whatever
  `CandidateInfluence.delta_t` values it's given.
