"""E4 -- the efficient frontier (COOLBLOCK-BUILD-PLAN.md §6.5 E4): "the
single most persuasive artefact for the business-strategy judge, stated
in her native language: diminishing returns, marginal cost of outcome."

Re-solves the real candidate universe across a budget sweep ($5k-$500k,
the plan's own range) with E2's CELF greedy, producing a benefit-vs-budget
curve and the marginal EWCB delivered per additional $1,000 spent.

**Each budget is solved fresh, not incrementally extended from the
previous one.** CELF's own `solve()` picks the better of cost-effective
greedy and the single best affordable candidate
(`engine.optimize.celf`'s module docstring) -- which of the two wins can
differ between budgets, so a larger budget's selection is not guaranteed
to be a superset of a smaller budget's. Re-solving from scratch at every
point is the honest choice over assuming monotonic nesting that the
solver itself does not guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from engine.optimize.celf import solve
from engine.optimize.objective import CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]

BUDGET_SWEEP_MIN_USD = 5_000.0
BUDGET_SWEEP_MAX_USD = 500_000.0
BUDGET_SWEEP_STEP_USD = 10_000.0  # 50 points across the plan's $5k-$500k range -- a real tradeoff against sweep runtime, disclosed here rather than hidden in a magic number


@dataclass(frozen=True)
class FrontierPoint:
    budget_usd: float
    objective_value: float
    cost_usd: float
    n_candidates_selected: int
    marginal_value_per_1000usd: float  # vs. the previous point in the sweep


def default_budget_sweep() -> list[float]:
    """$5k-$500k in $10k steps, with the exact max always included even
    though the range (495,000) isn't an integer multiple of the step
    (a real off-by-one this project caught during Phase 6 development --
    naively rounding `(max - min) / step` overshot to $505,000)."""
    budgets = list(np.arange(BUDGET_SWEEP_MIN_USD, BUDGET_SWEEP_MAX_USD, BUDGET_SWEEP_STEP_USD))
    budgets.append(BUDGET_SWEEP_MAX_USD)
    return [float(b) for b in budgets]


def compute_efficient_frontier(
    objective: CoverageObjective,
    costs: FloatArray,
    budgets_usd: list[float] | None = None,
) -> list[FrontierPoint]:
    budgets = sorted(budgets_usd if budgets_usd is not None else default_budget_sweep())

    points: list[FrontierPoint] = []
    previous_value, previous_budget = 0.0, 0.0
    for budget in budgets:
        picks = list(solve(objective, costs, budget))
        value = picks[-1].cumulative_value if picks else 0.0
        cost = picks[-1].cumulative_cost_usd if picks else 0.0

        delta_budget = budget - previous_budget
        marginal = (value - previous_value) / (delta_budget / 1000.0) if delta_budget > 0 else 0.0

        points.append(
            FrontierPoint(
                budget_usd=budget,
                objective_value=value,
                cost_usd=cost,
                n_candidates_selected=len(picks),
                marginal_value_per_1000usd=marginal,
            )
        )
        previous_value, previous_budget = value, budget

    return points
