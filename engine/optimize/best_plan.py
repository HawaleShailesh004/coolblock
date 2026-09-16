"""The plan CoolBlock actually hands a user: proven optimal when that is
cheap to prove, the fast greedy answer otherwise (docs/adr/0028-*.md).

CELF (`engine.optimize.celf`) is fast and carries a worst-case guarantee,
but a guarantee isn't the best answer. Measured on the default pool -- the
773 public-land tree sites -- HiGHS's exact MILP (`engine.optimize.exact`)
proves the optimal plan in ~1.5-2 s at every budget from $5k to $500k, and
that plan delivers 0-16% more equity-weighted cooling than CELF's (16% at
$20,000). Handing out the greedy plan when the provably best one costs two
seconds would be leaving real cooling on the table.

So: pools up to `EXACT_POOL_LIMIT` candidates get an exact solve under a
wall-clock limit. If HiGHS proves optimality in time (and, defensively, the
result is at least as good as greedy), that plan is used; otherwise --
a slow machine, a larger pool like private cool roofs -- the CELF plan is
used and labeled as such. Either way the caller learns which one it got.

The exact solver returns a set, not an order. Sites are emitted in order of
contribution (each next site is the one adding the most cooling given the
ones already listed), so the live "sites landing one at a time" view and the
ranked table still read top-down, and their running totals end exactly at
the plan's value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from engine.optimize.celf import Selection, solve
from engine.optimize.exact import solve_exact
from engine.optimize.objective import CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]

EXACT_POOL_LIMIT = 1_000
EXACT_TIME_LIMIT_S = 10.0

Solver = Literal["exact_milp", "celf"]


@dataclass(frozen=True)
class BestPlan:
    picks: list[Selection]
    solver: Solver
    proven_optimal: bool

    @property
    def value(self) -> float:
        return self.picks[-1].cumulative_value if self.picks else 0.0

    @property
    def cost_usd(self) -> float:
        return self.picks[-1].cumulative_cost_usd if self.picks else 0.0


def order_by_contribution(
    objective: CoverageObjective, costs: FloatArray, selected: frozenset[int]
) -> list[Selection]:
    """Lists a fixed set of sites so each next one adds the most cooling
    given the ones before it. Ties break by candidate index, so the order is
    deterministic."""
    remaining = set(selected)
    current_max = np.zeros(objective.n_population, dtype="float64")
    picks: list[Selection] = []
    value = cost = 0.0
    while remaining:
        best = max(sorted(remaining), key=lambda i: objective.marginal_gain(i, current_max))
        gain = objective.marginal_gain(best, current_max)
        objective.apply(best, current_max)
        remaining.remove(best)
        value += gain
        cost += float(costs[best])
        picks.append(
            Selection(
                candidate_index=best,
                cost_usd=float(costs[best]),
                marginal_gain=gain,
                cumulative_value=value,
                cumulative_cost_usd=cost,
            )
        )
    return picks


def best_plan(
    objective: CoverageObjective,
    costs: FloatArray,
    budget_usd: float,
    exact_pool_limit: int = EXACT_POOL_LIMIT,
    time_limit_s: float = EXACT_TIME_LIMIT_S,
) -> BestPlan:
    greedy = list(solve(objective, costs, budget_usd))
    greedy_value = greedy[-1].cumulative_value if greedy else 0.0

    if len(objective.influences) <= exact_pool_limit:
        exact = solve_exact(
            objective, costs, budget_usd, time_limit_s=time_limit_s, max_candidates=exact_pool_limit
        )
        if exact.is_proven_optimal and exact.objective_value >= greedy_value - 1e-6:
            return BestPlan(
                order_by_contribution(objective, costs, exact.selected), "exact_milp", True
            )

    return BestPlan(greedy, "celf", False)
