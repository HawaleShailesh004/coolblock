"""E5 -- the baselines (COOLBLOCK-BUILD-PLAN.md §6.5 E5), "the proof the
product works." Solves the same candidate universe and budget with four
naive/status-quo strategies, then compares each one's resulting
`CoverageObjective` value (D4's EWCB, the same real metric CoolBlock
itself maximizes) against CoolBlock's own CELF solve.

    "If CoolBlock does not beat TES-score-only by a clear margin, we have
    not built anything and we need to know that on day 5, not day 13."

All four baselines are real, deterministic (or seeded) selection rules
against this neighborhood's actual candidates and actual Census/TES data
-- not simulated or hand-waved comparisons.

- **Spread evenly**: `budget / n_zones` per real Census block group
  (D7b), spent on that zone's own candidates in a fixed order until
  exhausted. A zone with fewer/cheaper candidates than its allocation
  simply leaves that portion unspent -- no cross-subsidy between zones,
  which is the actual behavior "equal spend per block group" describes.
- **Worst-first**: candidates ranked by the real downscaled 10m LST
  (`engine.thermal.downscale`) sampled at each candidate's own location,
  hottest first, greedily filling the budget.
- **Squeaky wheel**: randomized selection (seeded, reproducible) weighted
  by each candidate's block group's real median household income (D7) --
  the documented status-quo bias the plan names it after.
- **TES-score-only**: candidates ranked by their block group's real Tree
  Equity Score (D10, a third-party public mirror -- see
  `engine.ingest.d10_tree_equity_score`'s module docstring for the
  provenance caveat already disclosed there), lowest (worst tree equity)
  first, greedily filling the budget.

**Disclosed scope limit**: a candidate whose centroid falls outside every
zone a given baseline's zoning data covers (D7b covers 18 of 23 block
groups, `docs/adr/0006-*.md`; D10 covers 13) is not selectable by that
particular baseline -- not silently included with a guessed zone, and not
excluded from CoolBlock's own solve, which has no such zone dependency.
This means each baseline's candidate *pool* can differ slightly; the
comparison is still fair because every strategy is solving the real
budget-constrained selection problem against the real data available to
it, exactly as a planner using that strategy actually would be limited.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from engine.ingest import d07_census, d07b_tiger_bg, d10_tree_equity_score
from engine.ingest.grid import get_canonical_grid
from engine.ingest.manifest import version_dir
from engine.optimize.celf import solve
from engine.optimize.objective import CoverageObjective
from engine.thermal.downscale import run_downscaling

FloatArray = np.ndarray[Any, np.dtype[np.float64]]

SQUEAKY_WHEEL_SEED = 20260905  # today's build date -- fixed so the "documented status quo" baseline is reproducible


def assign_block_group(candidates: gpd.GeoDataFrame) -> pd.Series:
    """Each candidate's real D7b block-group GEOID, or NaN if its centroid
    falls outside D7b's coverage (see module docstring)."""
    block_groups = gpd.read_parquet(version_dir(d07b_tiger_bg.SOURCE_ID, d07b_tiger_bg.VERSION) / "block_groups.parquet")
    block_groups = block_groups.to_crs(candidates.crs)

    centroids = gpd.GeoDataFrame(geometry=candidates.geometry.centroid, crs=candidates.crs)
    joined = gpd.sjoin(centroids, block_groups[["GEOID", "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]
    return pd.Series(joined["GEOID"].to_numpy(), index=candidates.index)


def assign_tes_score(candidates: gpd.GeoDataFrame) -> pd.Series:
    """Each candidate's real D10 Tree Equity Score, or NaN outside D10's
    coverage."""
    tes = gpd.read_parquet(version_dir(d10_tree_equity_score.SOURCE_ID, d10_tree_equity_score.VERSION) / "tes_block_groups.parquet")
    tes = tes.to_crs(candidates.crs)

    centroids = gpd.GeoDataFrame(geometry=candidates.geometry.centroid, crs=candidates.crs)
    joined = gpd.sjoin(centroids, tes[["tes", "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]
    return pd.Series(joined["tes"].to_numpy(), index=candidates.index)


def _median_income_by_block_group() -> pd.Series:
    acs = pd.read_parquet(version_dir(d07_census.SOURCE_ID, d07_census.VERSION) / "acs5_block_groups.parquet")
    income = pd.to_numeric(acs["median_household_income"], errors="coerce")
    return pd.Series(income.to_numpy(), index=acs["geoid"].to_numpy())


def _sample_local_lst(candidates: gpd.GeoDataFrame) -> FloatArray:
    grid = get_canonical_grid()
    lst = run_downscaling().lst_10m.values.astype("float64")
    values = np.full(len(candidates), np.nan, dtype="float64")
    for i, geom in enumerate(candidates.geometry.centroid):
        col, row = ~grid.transform * (geom.x, geom.y)
        row_i = int(np.clip(round(row), 0, grid.height - 1))
        col_i = int(np.clip(round(col), 0, grid.width - 1))
        values[i] = lst[row_i, col_i]
    return values


def _greedy_fill_by_priority(order: list[int], costs: FloatArray, budget: float) -> set[int]:
    """Shared mechanism for the rank-then-fill baselines (worst-first,
    TES-score-only): walk a priority order, take whatever fits."""
    selected: set[int] = set()
    spent = 0.0
    for i in order:
        cost = costs[i]
        if spent + cost <= budget:
            selected.add(i)
            spent += cost
    return selected


def spread_evenly(candidates: gpd.GeoDataFrame, costs: FloatArray, budget_usd: float) -> set[int]:
    block_group = assign_block_group(candidates)
    zones = block_group.dropna().unique()
    if len(zones) == 0:
        return set()
    per_zone_budget = budget_usd / len(zones)

    selected: set[int] = set()
    for zone in zones:
        zone_indices = np.flatnonzero((block_group == zone).to_numpy())
        spent = 0.0
        for i in zone_indices:  # fixed order: candidate array order, deterministic
            cost = costs[i]
            if spent + cost <= per_zone_budget:
                selected.add(int(i))
                spent += cost
    return selected


def worst_first(candidates: gpd.GeoDataFrame, costs: FloatArray, budget_usd: float) -> set[int]:
    local_lst = _sample_local_lst(candidates)
    order = list(np.argsort(-np.nan_to_num(local_lst, nan=-np.inf)))
    return _greedy_fill_by_priority(order, costs, budget_usd)


def tes_score_only(candidates: gpd.GeoDataFrame, costs: FloatArray, budget_usd: float) -> set[int]:
    tes_score = assign_tes_score(candidates)
    eligible = tes_score.notna().to_numpy()
    order = [i for i in np.argsort(tes_score.fillna(np.inf).to_numpy()) if eligible[i]]
    return _greedy_fill_by_priority(order, costs, budget_usd)


def squeaky_wheel(
    candidates: gpd.GeoDataFrame, costs: FloatArray, budget_usd: float, seed: int = SQUEAKY_WHEEL_SEED
) -> set[int]:
    block_group = assign_block_group(candidates)
    income_by_bg = _median_income_by_block_group()
    candidate_income = block_group.map(income_by_bg)

    eligible_mask = candidate_income.notna().to_numpy()
    eligible_indices = np.flatnonzero(eligible_mask)
    if eligible_indices.size == 0:
        return set()

    weights = candidate_income.to_numpy()[eligible_indices].astype("float64")
    weights = np.clip(weights, 1.0, None)  # a real income of 0 shouldn't zero out selection probability entirely
    probabilities = weights / weights.sum()

    rng = np.random.default_rng(seed)
    order = rng.choice(eligible_indices, size=len(eligible_indices), replace=False, p=probabilities)
    return _greedy_fill_by_priority(list(order), costs, budget_usd)


def coolblock(objective: CoverageObjective, costs: FloatArray, budget_usd: float) -> set[int]:
    return {p.candidate_index for p in solve(objective, costs, budget_usd)}


def run_all_baselines(
    candidates: gpd.GeoDataFrame, objective: CoverageObjective, costs: FloatArray, budget_usd: float
) -> dict[str, float]:
    """Runs all five strategies and returns each one's real EWCB value
    (via the same `CoverageObjective`, so every strategy is scored by the
    same yardstick CoolBlock itself maximizes)."""
    strategies = {
        "spread_evenly": spread_evenly(candidates, costs, budget_usd),
        "worst_first": worst_first(candidates, costs, budget_usd),
        "squeaky_wheel": squeaky_wheel(candidates, costs, budget_usd),
        "tes_score_only": tes_score_only(candidates, costs, budget_usd),
        "coolblock": coolblock(objective, costs, budget_usd),
    }
    return {name: objective.value(selection) for name, selection in strategies.items()}
