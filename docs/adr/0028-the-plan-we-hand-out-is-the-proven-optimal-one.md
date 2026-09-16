# 28. The plan we hand out is the proven-optimal one, not the greedy one

Date: 2026-09-16

## Status

Accepted. Changes which solver produces the plan for the default
candidate pool, revisiting the approximation-ratio argument in
[`0012-optimizer-coverage-objective-and-approximation-ratio.md`](0012-optimizer-coverage-objective-and-approximation-ratio.md),
and promotes the exact MILP built for measurement (E2,
`engine/optimize/exact.py`) into the live path. Only possible because
[`0027-programs-trees-and-cool-roofs-never-ranked-together.md`](0027-programs-trees-and-cool-roofs-never-ranked-together.md)
shrank the default pool to 773 candidates.

## Context

CELF (`engine/optimize/celf.py`) was the production solver because it is fast and
carries a `(1 - 1/√e)` ≈ 39% worst-case guarantee on a submodular
objective. The exact MILP existed only to *measure* how close greedy actually got,
on a reduced 300-candidate instance.

Writing the marketing page forced a check of a claim carried over from
that measurement — "within 0.4% of exact." It was measured on the *old*
mixed pool. On the pool the product actually solves since ADR-0027 (773
tree sites on public land), it is not true. Measured, same objective,
same costs, 10 s limit:

| Budget | CELF | Exact | CELF / exact | Exact solve |
|---|---|---|---|---|
| $5,000 | 1,436 | 1,521 | 94.4% | proven optimal, 1.4 s |
| $20,000 | 3,496 | 4,057 | **86.2%** | proven optimal, 1.6 s |
| $50,000 | 11,359 | 11,775 | 96.5% | proven optimal, 1.9 s |
| $100,000 | 17,734 | 18,179 | 97.6% | proven optimal, 2.0 s |
| $200,000 | 23,010 | 23,021 | 99.95% | proven optimal, 1.8 s |
| $500,000 | 25,678 | 25,808 | 99.5% | proven optimal, 1.5 s |

At $20,000 — the budget a real neighbourhood tree grant is closest to,
and the one the homepage shows — greedy leaves **16% of the available
cooling on the table**. Every solve was proven optimal in under two
seconds.

Handing a city the greedy plan when the provably best plan costs two more
seconds is not a defensible trade. The guarantee was the right *promise*
when the pool was 4,371 mixed candidates; it is not the right *answer*
when the optimum is this cheap to prove.

## Decision

`engine.optimize.best_plan.best_plan()` is the one place a plan is
produced. It:

1. Solves with CELF (fast, always available).
2. If the pool is ≤ `EXACT_POOL_LIMIT` (1,000) candidates, also solves
   the exact MILP under a 10 s wall clock.
3. Uses the exact plan **only if HiGHS proved optimality and its value is
   at least greedy's** — a defensive floor, so a solver quirk can never
   hand out a worse plan than the one we already had.
4. Otherwise returns the CELF plan.

`DoneEvent.solver` reports which ran (`"exact_milp"` or `"celf"`), so the
API, the memo and the UI always say what actually produced the plan. Side
constraints (E3) still route to `constrained_greedy` — the MILP does not
model them.

The MILP returns a *set*, with no order. `order_by_contribution()` lists
it so each next site is the one adding the most cooling given the ones
before it. That keeps the live "sites landing one at a time" animation and
the ranked table honest: ranks are real marginal contributions, and the
running totals end exactly at the plan's value.

Every producer of a plan goes through this one function —
`plan_service.stream_solve` (the app), `baselines.coolblock` (the
comparison chart) and `scripts/export_map_layers.py` (the static map
layer). A baseline chart that scored CoolBlock with a *weaker* solver than
the product uses would flatter the baselines and misstate the product.

## Consequences

- The default plan is now provably the best set of sites for the money,
  on this pool, and we can say so.
- A solve costs ~2 s more. The optimizer's live progress animation was
  already real work, not theatre; it now has slightly more of it.
- **The baseline multiples change**, because CoolBlock's own score went
  up. `docs/METHODOLOGY.md` carries the re-measured table.
- Larger pools — cool roofs on any land (2,842 candidates), or a future
  second neighbourhood — exceed `EXACT_POOL_LIMIT` and get CELF, labeled
  CELF. That is the honest fallback, not a hidden downgrade: the solver
  name travels with the plan.
- If HiGHS ever times out without proving optimality, the user gets the
  greedy plan rather than an unproven one. Silence is not an option the
  code has.
- `engine/optimize/frontier.py` still sweeps budgets with CELF. It sweeps
  dozens of budgets per call and nothing user-facing reads it yet; if it
  is ever surfaced next to a plan, it has to move to `best_plan` too, or
  the curve will sit below the plan it is supposed to explain.
