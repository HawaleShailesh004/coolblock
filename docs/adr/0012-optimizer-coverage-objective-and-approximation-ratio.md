# 12. Optimizer: coverage-function objective, HVI floor, corrected approximation ratio

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §6.5 E1 states the project's central technical
claim: maximizing EWCB under a budget is submodular maximization under a
knapsack constraint, "NP-hard, and *not* solvable by sorting sites by
score," because "two trees 8m apart do not deliver double the cooling."
D4's `EWCB(S) = Σ_p ΔT_S(x_p) · HVI(p) · exposure(p) · hours(p)`
(`engine.impact.ewcb`) was built in Phase 5 to *report* one candidate's
own benefit -- it sums independently per candidate, which is exactly the
"sort by score" structure the plan says is wrong for a *set*. Building the
actual optimizer required resolving that gap, plus two more that only
surfaced once real code was written against it.

## Decision

**1. EWCB becomes a weighted coverage function for optimization
purposes**, in `engine/optimize/objective.py`:

    F(S) = Σ_p  weight(p) · max_{i ∈ S} ΔT_i(x_p)

taking the *max* ΔT any selected candidate delivers to a given population
point, not the sum -- a canonical monotone submodular structure (adding a
candidate can only raise, never lower, a point's max; the marginal gain
from one more candidate shrinks as more of the "cooling ground" is already
covered by an existing high-ΔT candidate). This is the actual mathematical
object the plan's submodularity claim needs, built from the same real
per-candidate ΔT fields C1 and C3 already produce, not asserted without
structure.

**2. HVI is floored at 0 for the optimizer's objective only.** D2's HVI
is a signed z-score (`docs/METHODOLOGY.md`), and D4 deliberately keeps
that sign for transparent reporting (`docs/adr/0010-*.md`). A coverage
function with a negative-weighted point is not monotone -- selecting a
candidate that newly reaches a below-average-vulnerability point would
*decrease* F(S), which breaks CELF's approximation guarantee and directly
contradicts the Phase 6 DoD's own property test ("benefit monotone in
budget"). `OPTIMIZER_HVI_FLOOR = 0.0` in `objective.py` clips HVI so a
below-average-vulnerability point contributes zero optimizer weight
(neither reward nor penalty) rather than a negative one. This changes
nothing about what D4 reports per candidate -- it is strictly an internal
requirement of the set-function objective the optimizer maximizes.

**3. The plan's stated `(1 - 1/e) ~= 0.63` CELF guarantee is corrected
for the knapsack setting.** That bound is exact for *cardinality*-
constrained submodular maximization (each pick costs one "slot").
Candidates here have real, heterogeneous dollar costs -- a knapsack
constraint -- and the correctly-citable worst-case guarantee for
cost-effective greedy under a knapsack is `(1 - 1/sqrt(e)) ~= 0.393`
(Khuller, Moss, Naor 1999), achieved by taking the better of (a) greedy by
marginal-gain-per-dollar and (b) the single best affordable candidate on
its own -- both implemented in `engine/optimize/celf.py`
(`greedy_by_ratio`, `best_single_candidate`, and `solve`'s comparison of
the two). Restating the plan's cardinality-case figure without this
caveat would have been a real, avoidable inaccuracy in a project whose
explicit posture is "every coefficient is stored with its source."

**4. The exact MILP solver's formulation is exact, not a linearized
approximation.** `engine/optimize/exact.py` uses per-(population point,
candidate) binary "achiever" variables (`z[p,i] <= x_i`, at most one
achiever per point) rather than a big-M relaxation of the max. Because
every objective coefficient is non-negative, the solver is incentivized
to pick the true highest-ΔT active candidate as each point's achiever,
exactly reproducing `CoverageObjective.value()` at the optimum. Verified
against real brute-force enumeration on small instances
(`engine/tests/test_exact.py`).

## Consequences

- The Phase 6 DoD's literal property-test bar ("greedy >= 0.63 x exact on
  every small instance") is checked *empirically* against a real
  brute-force optimum on small synthetic instances
  (`engine/tests/test_celf.py::test_greedy_reaches_at_least_063_of_exact_on_small_instances`),
  not assumed from either theoretical bound -- and it passes. What the DoD
  actually gates on is the measured ratio, which is what is reported, not
  which textbook guarantee applies in the worst case.
- `cool_pavement` and `shade_structure` candidates always have an empty
  `CandidateInfluence` (D4's own disclosed scope gap, §6.4 D4 in
  `docs/METHODOLOGY.md`) -- the optimizer will never select either for
  *equity* credit under this objective. Their cost is real; their EWCB
  marginal gain is exactly zero. If a future phase adds an occupancy or
  exposure model for either type, `build_coverage_objective`'s per-type
  branch is the place to extend, not `celf.py`.
- Measured on the real, full candidate universe (4,371 candidates, 2,401
  population points): `build_coverage_objective` takes under 1 second;
  `solve()` takes 0.05-0.2 seconds across budgets from $5,000 to $5
  million -- well inside the Phase 6 DoD's "< 8s for the full
  neighborhood" bar, with room to spare for the local-search pass still
  to come.
- Measured on a real 300-candidate reduced instance (the plan's own
  specified size): greedy reaches 99.6-99.9% of HiGHS's *proven* exact
  optimum, solved in 1-2 seconds. This is far above both the plan's cited
  cardinality-case figure and the knapsack-correct worst-case bound --
  worth stating as "measured, not the worst case" in the writeup, per
  `docs/METHODOLOGY.md`'s optimizer section, rather than implied to be a
  guaranteed result.
