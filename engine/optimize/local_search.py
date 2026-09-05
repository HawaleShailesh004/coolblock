"""E2 (third solver) -- local search improvement pass
(COOLBLOCK-BUILD-PLAN.md §6.5 E2): "swap / 2-opt / budget-rebalance on
the greedy solution... squeezes the last 2-5%; makes the result
defensible against 'why not this obvious swap?'"

**Scope, disclosed up front.** A full 2-opt sweep (every selected
candidate against every unselected one) is `O(|S| · |not S|)` value
recomputations -- for the real candidate universe (a few hundred selected
out of ~4,300) that is well into the millions of `CoverageObjective.value()`
calls, each itself `O(total influence size)`. This implementation instead
restricts the swap-in pool to the `SWAP_POOL_SIZE` unselected candidates
with the highest *standalone* marginal gain (the same ranking
`engine.optimize.exact.reduce_instance` uses) -- the candidates most
likely to matter, not an exhaustive search. This is a real, bounded local
search, not a full 2-opt; the bound is the honest tradeoff for running in
real time against the full neighborhood, disclosed here rather than
silently narrowed.

Each iteration tries swapping out the selection's own *least* valuable
member (smallest individual marginal contribution to the final selection)
for the best-fitting candidate in the swap pool, keeping the swap only if
it provably raises `CoverageObjective.value()` -- an exact check, not an
estimate, since with the selection already small after CELF, recomputing
`value()` from scratch per candidate swap is cheap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from engine.optimize.objective import CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]

SWAP_POOL_SIZE = 50
MAX_ITERATIONS = 10


@dataclass(frozen=True)
class LocalSearchResult:
    selected: frozenset[int]
    objective_value: float
    cost_usd: float
    n_swaps_applied: int
    n_iterations_run: int


def _standalone_gain(objective: CoverageObjective, candidate_index: int) -> float:
    zero = np.zeros(objective.n_population, dtype="float64")
    return objective.marginal_gain(candidate_index, zero)


def _own_contribution(objective: CoverageObjective, selected: set[int], i: int, value_with_all: float) -> float:
    """How much `value(selected)` would drop if `i` alone were removed --
    the exact per-member contribution, accounting for the fact that
    another selected candidate may already cover some of the same ground
    (so removing `i` can cost less than its standalone gain). Caller
    passes `value_with_all` (computed once per pass) rather than
    recomputing it for every candidate."""
    return value_with_all - objective.value(selected - {i})


def local_search(
    objective: CoverageObjective,
    costs: FloatArray,
    budget_usd: float,
    initial_selection: set[int],
    swap_pool_size: int = SWAP_POOL_SIZE,
    max_iterations: int = MAX_ITERATIONS,
) -> LocalSearchResult:
    """Improves `initial_selection` (typically CELF's output) via bounded
    single-candidate swaps. Never returns a selection worse than the
    input, and never exceeds `budget_usd`."""
    selected = set(initial_selection)
    unselected = [i for i in range(len(objective.influences)) if i not in selected]

    swap_pool = sorted(unselected, key=lambda i: -_standalone_gain(objective, i))[:swap_pool_size]

    current_value = objective.value(selected)
    current_cost = float(sum(costs[i] for i in selected))
    n_swaps = 0
    iteration = 0

    for iteration in range(1, max_iterations + 1):  # noqa: B007 -- used after the loop, in the returned result
        if not selected:
            break
        # Try swap-out candidates in ascending order of their own exact
        # contribution -- the least valuable member is the best swap target.
        removal_order = sorted(selected, key=lambda i: _own_contribution(objective, selected, i, current_value))

        best_swap: tuple[int, int, float] | None = None  # (remove, add, new_value)
        for remove_i in removal_order:
            budget_after_removal = budget_usd - (current_cost - costs[remove_i])
            for add_j in swap_pool:
                if add_j in selected or costs[add_j] > budget_after_removal:
                    continue
                candidate_selection = (selected - {remove_i}) | {add_j}
                new_value = objective.value(candidate_selection)
                if new_value > current_value and (best_swap is None or new_value > best_swap[2]):
                    best_swap = (remove_i, add_j, new_value)
            if best_swap is not None:
                break  # first improving swap-out target found this pass; apply and re-evaluate

        if best_swap is None:
            break

        remove_i, add_j, new_value = best_swap
        selected = (selected - {remove_i}) | {add_j}
        swap_pool = [i for i in swap_pool if i != add_j] + [remove_i]
        current_value = new_value
        current_cost = float(sum(costs[i] for i in selected))
        n_swaps += 1

    return LocalSearchResult(
        selected=frozenset(selected),
        objective_value=current_value,
        cost_usd=current_cost,
        n_swaps_applied=n_swaps,
        n_iterations_run=iteration,
    )
