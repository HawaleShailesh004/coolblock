"""E2 (second solver) -- exact MILP solve on a reduced instance
(COOLBLOCK-BUILD-PLAN.md §6.5 E2): "proves how close greedy actually
gets," using HiGHS via `highspy`.

**The MILP formulation is exact, not a linearized approximation of the
coverage objective.** For each candidate `i`, a binary `x_i` (selected or
not). For each (population point `p`, candidate `i`) pair where `i`
influences `p`, a binary `z[p, i]` meaning "`i` is the achiever of `p`'s
covered ΔT" -- i.e. the candidate whose contribution `max_{j ∈ S} ΔT_j(p)`
actually equals. Two linear constraints per point tie `z` to `x` and to
each other:

    z[p, i] <= x_i                 (i can only be an achiever if selected)
    Σ_i z[p, i] <= 1                (at most one achiever per point)

The objective, `maximize Σ_{p,i} weight(p) · ΔT_i(p) · z[p, i]`, is
purely linear in `z` (every coefficient is a precomputed constant), and
because every coefficient is non-negative, the solver is *incentivized*
to set `z[p, i] = 1` for whichever active candidate has the single
highest `ΔT_i(p)` at each point -- exactly reproducing
`CoverageObjective.value()` at the optimum, without a big-M relaxation or
any approximation of the max. This is what "exact" means here.

Restricted to a **reduced instance** (`MAX_EXACT_CANDIDATES`, a few
hundred) because the number of `(p, i)` pairs -- and therefore binary
variables -- scales with total candidate-to-population influence, and a
MILP over the full ~4,300-candidate universe is not the point: the DoD
asks for the measured greedy/exact *ratio*, which this reduced instance
gives directly and HiGHS can solve to proven optimality (or a small,
reported gap) within a real time budget.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import highspy
import numpy as np

from engine.optimize.objective import CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]
IntArray = np.ndarray[Any, np.dtype[np.int64]]

MAX_EXACT_CANDIDATES = 300
DEFAULT_TIME_LIMIT_S = 30.0


@dataclass(frozen=True)
class ExactSolution:
    selected: frozenset[int]
    objective_value: float
    cost_usd: float
    status: str
    solve_time_s: float
    is_proven_optimal: bool


def solve_exact(
    objective: CoverageObjective,
    costs: FloatArray,
    budget_usd: float,
    time_limit_s: float = DEFAULT_TIME_LIMIT_S,
) -> ExactSolution:
    """Exact MILP solve. Raises if `objective` has more than
    `MAX_EXACT_CANDIDATES` candidates -- callers must pass a reduced
    instance (see `reduce_instance` below), not silently truncate here."""
    n = len(objective.influences)
    if n > MAX_EXACT_CANDIDATES:
        raise ValueError(f"{n} candidates exceeds MAX_EXACT_CANDIDATES ({MAX_EXACT_CANDIDATES}) -- reduce the instance first")

    h = highspy.Highs()
    h.silent()
    h.setOptionValue("time_limit", time_limit_s)

    x = h.addBinaries(n)

    z_vars: dict[tuple[int, int], Any] = {}
    objective_terms = []
    achievers_by_point: dict[int, list[int]] = {}
    for i, inf in enumerate(objective.influences):
        for p, delta_t in zip(inf.population_index.tolist(), inf.delta_t.tolist(), strict=True):
            z = h.addBinary()
            z_vars[(p, i)] = z
            h.addConstr(z <= x[i])
            achievers_by_point.setdefault(p, []).append(i)
            objective_terms.append(float(objective.weight[p]) * float(delta_t) * z)

    for p, achievers in achievers_by_point.items():
        h.addConstr(sum(z_vars[(p, i)] for i in achievers) <= 1)

    h.addConstr(sum(float(costs[i]) * x[i] for i in range(n)) <= budget_usd)

    if objective_terms:
        h.setObjective(sum(objective_terms), sense=highspy.ObjSense.kMaximize)
    else:
        h.setObjective(0 * x[0] if n > 0 else None, sense=highspy.ObjSense.kMaximize)

    t0 = time.time()
    h.run()
    solve_time = time.time() - t0

    status = h.getModelStatus()
    values = h.allVariableValues()
    selected = frozenset(i for i in range(n) if values[i] > 0.5)
    cost = float(sum(costs[i] for i in selected))
    obj_value = h.getObjectiveValue() if selected or objective_terms else 0.0

    return ExactSolution(
        selected=selected,
        objective_value=float(obj_value),
        cost_usd=cost,
        status=str(status),
        solve_time_s=solve_time,
        is_proven_optimal=status == highspy.HighsModelStatus.kOptimal,
    )


def reduce_instance(
    objective: CoverageObjective, costs: FloatArray, max_candidates: int = MAX_EXACT_CANDIDATES
) -> tuple[CoverageObjective, FloatArray, IntArray]:
    """Selects the `max_candidates` candidates with the highest standalone
    marginal gain (against an empty selection) -- a reduced instance that
    still contains the candidates greedy itself would consider first,
    rather than an arbitrary or random subset that could trivially favor
    one solver over the other. Returns the reduced objective, its costs,
    and the original indices (for mapping results back)."""
    n = len(objective.influences)
    if n <= max_candidates:
        return objective, costs, np.arange(n, dtype="int64")

    zero_max = np.zeros(objective.n_population, dtype="float64")
    standalone_gain = np.array([objective.marginal_gain(i, zero_max) for i in range(n)])
    top_indices: IntArray = np.argsort(-standalone_gain)[:max_candidates].astype("int64")
    top_indices = np.sort(top_indices)

    reduced_influences = [objective.influences[i] for i in top_indices]
    reduced_objective = CoverageObjective(
        influences=reduced_influences, weight=objective.weight, n_population=objective.n_population
    )
    return reduced_objective, costs[top_indices], top_indices
