"""E3 -- optimizer constraints (COOLBLOCK-BUILD-PLAN.md §6.5 E3): "all
real, all user-facing."

Implemented against this project's real data:

- **Budget cap** -- the base constraint every solver already enforces.
- **Maintenance-cost cap (annual)**. `ANNUAL_MAINTENANCE_USD_PER_TREE`
  ($75/yr) applies to tree-planting candidates, per unit planted,
  matching the plan's own cost table ("$400-1,200 planted + $75/yr").
  Cool-roof, cool-pavement, and shade-structure candidates default to
  $0/yr -- no maintenance-cost literature figure for any of those exists
  in this project's data, so zero is disclosed as "not modeled," not
  presented as a real zero.
- **Minimum spend per block group (an equity floor)**. A two-phase
  allocation: each real Census block group (D7b) first gets its floor
  spent on its own candidates (ranked by their own standalone
  contribution), then the standard constrained greedy runs on the
  remaining budget across the full universe (any zone can still receive
  more than its floor).
- **Maximum sites per block group** (visual/political dispersion) --
  enforced live during greedy selection via a running per-zone count.
- **Public-land-only mode** -- a real pre-filter on the `ownership` column
  (`public_row`/`public_parcel`) already computed by
  `engine.surface.candidates`/`impervious_candidates`.
- **Mandatory inclusion/exclusion** of specific candidate indices.

**Not implemented, disclosed rather than faked:**

- **Species diversity cap** ("no more than X% one genus"). No
  per-species or per-genus data exists for any candidate -- they are
  generic `street_tree`/`park_lot_tree_cluster` records, not species-level
  plantings. Enforcing a genus cap would require inventing species
  assignments this project has no basis for.
- **Water-budget cap**. No per-intervention irrigation or
  evapotranspiration demand estimate is ingested or modeled anywhere in
  this project.

**A real tradeoff, disclosed**: adding side constraints (per-zone counts,
a second running budget) breaks CELF's lazy-heap invariant -- a heap
entry's cached marginal gain can no longer be trusted stale, because a
per-zone cap or maintenance budget could newly bind between evaluations
in a way plain submodularity doesn't capture. `constrained_greedy` here is
a straightforward (non-lazy) greedy: recomputes every remaining
candidate's marginal gain each round. Slower than CELF per pick, but
correct under side constraints, and still fast enough in practice (see
`docs/METHODOLOGY.md`'s measured timings).

**Phase 7 addition: `ConstrainedResult.picks`.** The live-solve SSE stream
(`engine.optimize.plan_service`) needs to animate sites landing one at a
time (§9 ★2) for a constrained solve exactly as it already does for
CELF's own generator -- not just report the final set. Reuses CELF's own
`Selection` record type rather than inventing a second one, so both
solvers hand the API layer the same shape. This is a record of the order
`commit()` actually ran in and the true marginal gain at that moment
(recomputed once, cheaply, from each candidate's own influence set) --
not a re-sort of the final selection by some proxy ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engine.optimize.celf import Selection
from engine.optimize.objective import CoverageObjective

FloatArray = np.ndarray[Any, np.dtype[np.float64]]

ANNUAL_MAINTENANCE_USD_PER_TREE = 75.0
TREE_INTERVENTION_TYPES = frozenset({"street_tree", "park_lot_tree_cluster"})

PUBLIC_OWNERSHIP = frozenset({"public_row", "public_parcel"})


def annual_maintenance_cost(intervention_types: list[str], capacities: FloatArray) -> FloatArray:
    """Real, disclosed planning-estimate annual maintenance cost per
    candidate: $75/yr per planted tree unit (capacity) for tree-planting
    types, $0/yr (not modeled, not a measured zero) for everything else."""
    cost = np.zeros(len(intervention_types), dtype="float64")
    for i, itype in enumerate(intervention_types):
        if itype in TREE_INTERVENTION_TYPES:
            cost[i] = ANNUAL_MAINTENANCE_USD_PER_TREE * capacities[i]
    return cost


@dataclass(frozen=True)
class ConstraintConfig:
    budget_usd: float
    annual_maintenance_cap_usd: float | None = None
    min_spend_per_zone_usd: float | None = None
    max_sites_per_zone: int | None = None
    public_land_only: bool = False
    mandatory_include: frozenset[int] = field(default_factory=frozenset)
    mandatory_exclude: frozenset[int] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ConstrainedResult:
    selected: frozenset[int]
    objective_value: float
    cost_usd: float
    annual_maintenance_usd: float
    zone_spend_usd: dict[Any, float]
    zone_site_counts: dict[Any, int]
    picks: list[Selection] = field(default_factory=list)


def _eligible_mask(
    n: int,
    config: ConstraintConfig,
    ownership: list[str] | None,
) -> np.ndarray[Any, np.dtype[np.bool_]]:
    mask = np.ones(n, dtype=bool)
    if config.public_land_only:
        if ownership is None:
            raise ValueError("public_land_only requires an `ownership` list")
        mask &= np.array([o in PUBLIC_OWNERSHIP for o in ownership])
    for i in config.mandatory_exclude:
        mask[i] = False
    return mask


def constrained_greedy(
    objective: CoverageObjective,
    costs: FloatArray,
    config: ConstraintConfig,
    zone_ids: list[Any] | None = None,
    ownership: list[str] | None = None,
    maintenance_costs: FloatArray | None = None,
) -> ConstrainedResult:
    """A non-lazy constrained greedy (see module docstring for why it
    can't reuse CELF's lazy heap once side constraints are present).
    `zone_ids[i]` is candidate `i`'s real Census block-group GEOID
    (`engine.optimize.baselines.assign_block_group`); required for the
    zone-based constraints, ignored otherwise."""
    n = len(objective.influences)
    eligible = _eligible_mask(n, config, ownership)
    selected: set[int] = set()
    current_max = np.zeros(objective.n_population, dtype="float64")
    spent = 0.0
    maintenance_spent = 0.0
    zone_spend: dict[Any, float] = {}
    zone_counts: dict[Any, int] = {}
    picks: list[Selection] = []
    cumulative_value = 0.0

    def zone_of(i: int) -> Any:
        return zone_ids[i] if zone_ids is not None else None

    def can_afford(i: int) -> bool:
        if not eligible[i] or i in selected:
            return False
        if spent + costs[i] > config.budget_usd:
            return False
        if (
            maintenance_costs is not None
            and config.annual_maintenance_cap_usd is not None
            and maintenance_spent + maintenance_costs[i] > config.annual_maintenance_cap_usd
        ):
            return False
        return not (
            config.max_sites_per_zone is not None
            and zone_ids is not None
            and zone_counts.get(zone_of(i), 0) >= config.max_sites_per_zone
        )

    def commit(i: int) -> None:
        nonlocal spent, maintenance_spent, cumulative_value
        gain = objective.marginal_gain(i, current_max)
        objective.apply(i, current_max)
        selected.add(i)
        spent += costs[i]
        cumulative_value += gain
        if maintenance_costs is not None:
            maintenance_spent += maintenance_costs[i]
        zone = zone_of(i)
        zone_spend[zone] = zone_spend.get(zone, 0.0) + costs[i]
        zone_counts[zone] = zone_counts.get(zone, 0) + 1
        picks.append(
            Selection(
                candidate_index=i,
                cost_usd=float(costs[i]),
                marginal_gain=gain,
                cumulative_value=cumulative_value,
                cumulative_cost_usd=spent,
            )
        )

    # 1. Mandatory inclusions first, in the order given, subject only to
    # eligibility and budget -- a mandatory site the budget can't afford
    # is simply not included; this never silently exceeds the cap.
    for i in sorted(config.mandatory_include):
        if can_afford(i):
            commit(i)

    # 2. Minimum spend per zone -- each zone gets its floor spent on its
    # own most cost-effective eligible candidates (gain per dollar, same
    # ranking as the general phase) before the general phase runs.
    if config.min_spend_per_zone_usd is not None and zone_ids is not None:
        zones = sorted({z for z in zone_ids if z is not None})
        for zone in zones:
            zone_indices = [i for i in range(n) if zone_ids[i] == zone]
            while zone_spend.get(zone, 0.0) < config.min_spend_per_zone_usd:
                best_i, best_ratio = -1, 0.0
                for i in zone_indices:
                    if not can_afford(i):
                        continue
                    gain = objective.marginal_gain(i, current_max)
                    if gain <= 0:
                        continue
                    ratio = gain / costs[i]
                    if ratio > best_ratio:
                        best_i, best_ratio = i, ratio
                if best_i < 0:
                    break
                commit(best_i)

    # 3. General constrained greedy over everything still affordable --
    # ranked by marginal gain *per dollar* (cost-effectiveness), matching
    # E2's CELF (engine.optimize.celf), not raw marginal gain. Ranking by
    # raw gain alone is a much weaker knapsack heuristic (it favors a few
    # expensive high-value candidates over many cheap cost-effective
    # ones) -- caught by comparing this solver's unconstrained output
    # against CELF's on identical inputs and finding a large, unexplained
    # gap; this ranking is what closes it.
    while True:
        best_i, best_ratio = -1, 0.0
        for i in range(n):
            if not can_afford(i):
                continue
            gain = objective.marginal_gain(i, current_max)
            if gain <= 0:
                continue
            ratio = gain / costs[i]
            if ratio > best_ratio:
                best_i, best_ratio = i, ratio
        if best_i < 0:
            break
        commit(best_i)

    return ConstrainedResult(
        selected=frozenset(selected),
        objective_value=objective.value(selected),
        cost_usd=spent,
        annual_maintenance_usd=maintenance_spent,
        zone_spend_usd=zone_spend,
        zone_site_counts=zone_counts,
        picks=picks,
    )
