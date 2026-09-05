# 15. Efficient frontier: fresh solve per budget point, fixed a sweep off-by-one

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §6.5 E4 calls for "the full budget sweep" from
$5k to $500k, stored as an artifact, "the single most persuasive artefact
for the business-strategy judge... diminishing returns, marginal cost of
outcome."

Two real issues came up building `engine/optimize/frontier.py`:

1. **Should each budget point reuse the previous point's selection, or
   solve fresh?** E2's `solve()` (`engine.optimize.celf`) picks the better
   of cost-effective greedy and the single best affordable candidate --
   which of the two wins can differ between budgets, so a larger budget's
   optimal-ish selection is not guaranteed to be a superset of a smaller
   budget's.
2. **A real off-by-one in the sweep's endpoint.** The first
   implementation computed the number of steps as
   `round((500,000 - 5,000) / 10,000) + 1`. Since `495,000 / 10,000 =
   49.5` is not an integer, Python's round-half-to-even rounded it up to
   50, producing 51 steps and a last budget of $505,000 -- silently past
   the plan's own stated $500k ceiling. Caught by a test asserting the
   sweep's last point equals exactly $500,000.

## Decision

1. **Every budget point is solved fresh** (`compute_efficient_frontier`
   calls `solve()` independently per budget), not incrementally extended
   from the previous point's selection -- the honest choice given
   `solve()`'s own two-strategy comparison doesn't guarantee nesting.
2. **Fixed the sweep to always include the exact stated endpoints.**
   `default_budget_sweep()` now generates steps via `np.arange` up to (but
   not including) the max, then appends the exact max explicitly --
   guaranteed to hit $5,000 and $500,000 precisely regardless of whether
   the range divides evenly by the step size, rather than trusting a
   rounded step count.

## Consequences

- Measured on the real candidate universe (51 points, $5k-$500k in $10k
  steps): the sweep solves in ~2.2 seconds total (~45ms per point),
  producing a clean diminishing-returns curve -- marginal EWCB per
  additional $1,000 falls from the thousands at low budgets to double
  digits by $500k, exactly the shape the plan's own framing describes.
- Any future change to the sweep's step size or range should keep the
  "append the exact max" pattern rather than relying on the step count
  dividing the range evenly -- the kind of silent off-by-one this ADR
  documents is easy to reintroduce otherwise.
