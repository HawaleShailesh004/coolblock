"""E2 -- CELF lazy greedy under a budget constraint
(COOLBLOCK-BUILD-PLAN.md §6.5 E2), the production solver: "fast enough to
animate live."

**CELF** (Cost-Effective Lazy Forward selection, Leskovec et al. 2007)
exploits submodularity's diminishing-returns property directly: a
candidate's true marginal gain can only fall as more candidates are
already selected, never rise. So instead of recomputing every remaining
candidate's marginal gain on every iteration (`O(n)` per pick, `O(n·k)`
total), a max-heap keyed by each candidate's *last known* marginal-gain-
per-dollar is kept; the top of the heap is recomputed fresh, and if its
recomputed value is still ≥ the (necessarily-stale-or-equal) next-best
heap entry, it is provably still the best choice -- no other candidate
needs to be touched this round. In practice this is close to `O(n)` total
evaluations rather than `O(n·k)`, which is what makes this solver fast
enough to run interactively rather than only offline.

**On the approximation ratio.** The plan states "`(1 − 1/e) ≈ 0.63`
guarantee" for CELF. That bound is exact for *cardinality*-constrained
submodular maximization (each pick costs 1 "slot"). This problem is
**budget** (knapsack) constrained -- candidates have different dollar
costs -- and the correctly-citable worst-case guarantee for cost-effective
greedy under a knapsack is `(1 - 1/sqrt(e)) ≈ 0.393`
(Khuller, Moss, Naor 1999), achieved by taking the *better* of (a) greedy
by marginal-gain/cost ratio and (b) the single best affordable candidate
by raw value -- both of which this solver does
(`greedy_by_ratio` vs. `best_single_candidate`, `solve` returns whichever
wins). Restating the plan's `0.63` figure without this caveat would be a
real, avoidable inaccuracy; `docs/adr/0012-*.md` records the correction.
The Phase 6 DoD's own bar ("greedy ≥ 0.63 × exact on every small
instance") is an *empirical* property test, not a theoretical claim, and
is checked directly in `engine/tests/test_celf.py` against a real exact
solve on small instances -- what matters operationally is what is
actually measured, not which textbook bound applies.

Designed as a generator from the start (§6.5 E2's own requirement, "this
is what makes ★2 possible, and it must be designed in from the start"):
`solve()` yields each pick the moment it is confirmed, in spend order, so
a caller (the UI, `Phase 9`'s live animation) can render sites arriving
one at a time without waiting for the whole budget to be spent.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np

from engine.optimize.objective import CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]


@dataclass(frozen=True)
class Selection:
    candidate_index: int
    cost_usd: float
    marginal_gain: float
    cumulative_value: float
    cumulative_cost_usd: float


def _ratio_heap(costs: FloatArray, objective: CoverageObjective) -> list[tuple[float, int, int]]:
    """One heap entry per candidate: `(-gain/cost, staleness_marker, index)`.
    `staleness_marker` starts at 0 (computed against the empty selection);
    a popped entry is recomputed and re-pushed with an incremented marker
    if it is no longer the true best."""
    heap: list[tuple[float, int, int]] = []
    zero_max = np.zeros(objective.n_population, dtype="float64")
    for i, cost in enumerate(costs):
        if cost <= 0:
            continue
        gain = objective.marginal_gain(i, zero_max)
        if gain <= 0:
            continue
        heapq.heappush(heap, (-(gain / cost), 0, i))
    return heap


def greedy_by_ratio(
    objective: CoverageObjective, costs: FloatArray, budget_usd: float
) -> Iterator[Selection]:
    """Cost-effective lazy greedy: repeatedly picks the affordable
    candidate with the highest true marginal-gain-per-dollar, using CELF's
    lazy re-evaluation to avoid recomputing every candidate every round."""
    heap = _ratio_heap(costs, objective)
    current_max = np.zeros(objective.n_population, dtype="float64")
    selected: set[int] = set()
    cumulative_value = 0.0
    cumulative_cost = 0.0
    round_marker = 0

    while heap:
        neg_ratio, marker, i = heapq.heappop(heap)
        if i in selected:
            continue
        cost = costs[i]
        if cumulative_cost + cost > budget_usd:
            continue  # not affordable now; a cheaper candidate might still fit later

        if marker < round_marker:
            # Stale -- recompute the true current marginal gain and re-insert.
            gain = objective.marginal_gain(i, current_max)
            if gain <= 0:
                continue
            heapq.heappush(heap, (-(gain / cost), round_marker, i))
            continue

        # Fresh (recomputed this round, or never invalidated): confirmed best.
        gain = objective.marginal_gain(i, current_max)
        if gain <= 0:
            continue

        objective.apply(i, current_max)
        selected.add(i)
        cumulative_value += gain
        cumulative_cost += cost
        round_marker += 1

        yield Selection(
            candidate_index=i,
            cost_usd=float(cost),
            marginal_gain=gain,
            cumulative_value=cumulative_value,
            cumulative_cost_usd=cumulative_cost,
        )


def best_single_candidate(
    objective: CoverageObjective, costs: FloatArray, budget_usd: float
) -> Selection | None:
    """The single highest-value affordable candidate on its own --
    Khuller/Moss/Naor's safeguard against cost-effective greedy's worst
    case (a very cheap, low-value candidate crowding out one expensive,
    very high-value one)."""
    zero_max = np.zeros(objective.n_population, dtype="float64")
    best_i, best_gain = -1, 0.0
    for i, cost in enumerate(costs):
        if cost <= 0 or cost > budget_usd:
            continue
        gain = objective.marginal_gain(i, zero_max)
        if gain > best_gain:
            best_i, best_gain = i, gain
    if best_i < 0:
        return None
    return Selection(
        candidate_index=best_i,
        cost_usd=float(costs[best_i]),
        marginal_gain=best_gain,
        cumulative_value=best_gain,
        cumulative_cost_usd=float(costs[best_i]),
    )


def solve(objective: CoverageObjective, costs: FloatArray, budget_usd: float) -> Iterator[Selection]:
    """The full E2 solver: compares cost-effective lazy greedy against the
    single best affordable candidate and yields whichever achieves higher
    total value -- the standard fix that restores a provable
    `(1 - 1/sqrt(e))` worst-case guarantee under a knapsack constraint (see
    module docstring). Still a generator: the winning path's picks are
    yielded incrementally, in the order the winning strategy made them."""
    ratio_picks = list(greedy_by_ratio(objective, costs, budget_usd))
    ratio_value = ratio_picks[-1].cumulative_value if ratio_picks else 0.0

    single = best_single_candidate(objective, costs, budget_usd)
    single_value = single.marginal_gain if single is not None else 0.0

    if single is not None and single_value > ratio_value:
        yield single
    else:
        yield from ratio_picks
