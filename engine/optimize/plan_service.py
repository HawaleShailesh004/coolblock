"""Phase 7 -- the warm-solve path (COOLBLOCK-BUILD-PLAN.md §4.1): "the
expensive geospatial work is precomputed per neighborhood. What the user
triggers is only the optimizer over a prepared candidate set -- which is
fast, which is why the live optimizer animation can be real rather than
theatre."

This module is the one implementation `apps/api`'s ARQ worker (and any
future CLI/notebook caller) uses to run a solve and emit its stages as an
ordered event stream, so every caller sees identical solve semantics
rather than three independently-drifting copies. It reads the cached,
already-scored candidate universe
(`data/derived/<neighborhood>/candidates.geojson`, written by
`scripts/export_map_layers.py`'s `export_candidates()`) instead of
recomputing C1-C3/D1-D4 per request -- recomputing the full impact/equity
pipeline on every user interaction is the "cold pipeline" (20-90 min,
§4.1), the wrong path for something a user triggers by dragging a budget
slider.

Two solvers, selected automatically by which constraints are active,
matching E2/E3 exactly rather than reimplementing either:

- No side constraints beyond budget -> `engine.optimize.celf.solve`
  (CELF, the production solver, `(1 - 1/sqrt(e))` guarantee -- see that
  module's own docstring for the corrected citation).
- Any E3 side constraint active -> `engine.optimize.constraints.constrained_greedy`,
  which (Phase 7 addition) now also yields picks in true commit order so
  the SSE stream can animate a constrained solve exactly like a CELF one.

Both paths are exposed as one `stream_solve()` generator yielding a
uniform `SolveEvent` union (`StageEvent` / `SiteEvent` / `DoneEvent`) --
plain dataclasses, matching this engine package's convention everywhere
else (`Selection`, `ConstraintConfig`, `FrontierPoint`); `apps/api` (which
already depends on Pydantic for its own layer) converts these to JSON at
the API boundary, not here, so `engine` stays free of a web-framework
dependency.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np

from engine.config import load_neighborhood_config
from engine.optimize.baselines import assign_block_group
from engine.optimize.celf import Selection, solve
from engine.optimize.constraints import (
    ConstraintConfig,
    annual_maintenance_cost,
    constrained_greedy,
)
from engine.optimize.objective import build_coverage_objective

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Matches `scripts/export_map_layers.py`'s `OUT_DIR` exactly. A literal
# path, not a second lookup keyed off `config/neighborhood.toml`'s `id`
# field -- the scope lock (§1.3) means there is exactly one of these for
# the life of this build, so a second source of truth for the directory
# name would only be a place for the two to silently drift apart.
NEIGHBORHOOD_SLUG = "edison-eastlake"
CANDIDATES_PATH = REPO_ROOT / "data" / "derived" / NEIGHBORHOOD_SLUG / "candidates.geojson"


class CandidateUniverseMissing(RuntimeError):
    """Raised when the cached, scored candidate export hasn't been
    generated yet -- a real, actionable state, not silently substituted
    with an empty or fabricated universe."""


def load_candidate_universe(path: Path = CANDIDATES_PATH) -> gpd.GeoDataFrame:
    if not path.exists():
        raise CandidateUniverseMissing(
            f"{path} does not exist -- run `uv run python scripts/export_map_layers.py` first "
            "to build the scored candidate export this solver reads."
        )
    cfg = load_neighborhood_config()
    gdf = gpd.read_file(path)
    return gdf.to_crs(epsg=cfg.target_epsg)


@dataclass(frozen=True)
class SolveParams:
    """The E3 constraint surface (COOLBLOCK-BUILD-PLAN.md §6.5 E3), as the
    API layer will expose it. `mandatory_include`/`mandatory_exclude` are
    keyed by the candidate's stable `candidate_id` string (e.g.
    `"plant-00000-park_lot_tree_cluster"`), not its positional index --
    the index is an artifact of the current export's row order and isn't
    safe to persist across re-exports; the id is."""

    budget_usd: float
    public_land_only: bool = False
    max_sites_per_zone: int | None = None
    min_spend_per_zone_usd: float | None = None
    annual_maintenance_cap_usd: float | None = None
    mandatory_include_ids: frozenset[str] = field(default_factory=frozenset)
    mandatory_exclude_ids: frozenset[str] = field(default_factory=frozenset)

    def needs_constrained_solver(self) -> bool:
        """True iff any E3 side constraint beyond the plain budget cap is
        active -- CELF's lazy heap (E2) is only valid without these (see
        `engine.optimize.constraints`'s module docstring)."""
        return bool(
            self.public_land_only
            or self.max_sites_per_zone is not None
            or self.min_spend_per_zone_usd is not None
            or self.annual_maintenance_cap_usd is not None
            or self.mandatory_include_ids
            or self.mandatory_exclude_ids
        )


@dataclass(frozen=True)
class StageEvent:
    stage: str
    message: str


@dataclass(frozen=True)
class SiteEvent:
    rank: int
    candidate_id: str
    intervention_type: str
    cost_usd: float
    marginal_gain_ewcb: float
    cumulative_ewcb: float
    cumulative_cost_usd: float
    geometry: dict[str, Any]  # GeoJSON geometry, WGS84
    properties: dict[str, Any]


@dataclass(frozen=True)
class DoneEvent:
    solver: str  # "celf" | "constrained_greedy"
    n_sites: int
    total_cost_usd: float
    total_ewcb: float


SolveEvent = StageEvent | SiteEvent | DoneEvent


def _json_safe(value: Any) -> Any:
    """GeoDataFrame properties round-trip through pandas/numpy scalars
    (`numpy.float64`, `NaN` for genuinely-not-modeled fields like
    `cool_roof`'s `delta_t_peak_degc` -- see `engine.impact.ewcb`'s
    disclosed-gap pattern) -- neither is JSON-serializable as-is, and a
    bare NaN silently produces invalid JSON (`NaN` is not valid JSON)
    rather than an error, which is exactly the kind of silent failure
    this project's honesty rail exists to prevent."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def stream_solve(
    params: SolveParams,
    candidates: gpd.GeoDataFrame | None = None,
) -> Iterator[SolveEvent]:
    """Runs one solve and yields its stages, in order, as they actually
    happen -- the generator is the live progress stream itself (the ARQ
    worker forwards each yielded event to Redis as it arrives), not a
    batch result reshaped into fake progress after the fact.

    `candidates`, when given, is used instead of `load_candidate_universe()`
    -- what lets `engine/tests/test_plan_service.py` exercise this against
    a small synthetic universe without touching the real cached export."""
    yield StageEvent("loading_candidates", "Loading the cached, pre-scored candidate universe")
    universe = candidates if candidates is not None else load_candidate_universe()
    universe = universe.reset_index(drop=True)
    universe_wgs84 = universe.to_crs(epsg=4326)

    yield StageEvent("scoring_impact", "Building the equity-weighted coverage objective (D4)")
    objective = build_coverage_objective(universe)
    costs = universe["total_cost_usd"].to_numpy(dtype="float64")

    id_to_index = {str(cid): i for i, cid in enumerate(universe["candidate_id"])}
    mandatory_include = frozenset(id_to_index[c] for c in params.mandatory_include_ids if c in id_to_index)
    mandatory_exclude = frozenset(id_to_index[c] for c in params.mandatory_exclude_ids if c in id_to_index)

    def emit(pick: Selection, rank: int) -> SiteEvent:
        row = universe.iloc[pick.candidate_index]
        geometry_wgs84 = universe_wgs84.iloc[pick.candidate_index].geometry
        properties = {k: _json_safe(v) for k, v in row.drop(labels="geometry").to_dict().items()}
        return SiteEvent(
            rank=rank,
            candidate_id=str(row["candidate_id"]),
            intervention_type=str(row["intervention_type"]),
            cost_usd=pick.cost_usd,
            marginal_gain_ewcb=pick.marginal_gain,
            cumulative_ewcb=pick.cumulative_value,
            cumulative_cost_usd=pick.cumulative_cost_usd,
            geometry=json.loads(gpd.GeoSeries([geometry_wgs84], crs=4326).to_json())["features"][0]["geometry"],
            properties=properties,
        )

    if params.needs_constrained_solver():
        yield StageEvent("solving", "Running the constrained greedy solver (E3 side constraints active)")
        needs_zones = params.max_sites_per_zone is not None or params.min_spend_per_zone_usd is not None
        zone_ids = assign_block_group(universe).tolist() if needs_zones else None
        ownership = universe["ownership"].tolist() if params.public_land_only else None
        maintenance_costs = (
            annual_maintenance_cost(universe["intervention_type"].tolist(), universe["capacity"].to_numpy(dtype="float64"))
            if params.annual_maintenance_cap_usd is not None
            else None
        )
        config = ConstraintConfig(
            budget_usd=params.budget_usd,
            annual_maintenance_cap_usd=params.annual_maintenance_cap_usd,
            min_spend_per_zone_usd=params.min_spend_per_zone_usd,
            max_sites_per_zone=params.max_sites_per_zone,
            public_land_only=params.public_land_only,
            mandatory_include=mandatory_include,
            mandatory_exclude=mandatory_exclude,
        )
        result = constrained_greedy(
            objective, costs, config, zone_ids=zone_ids, ownership=ownership, maintenance_costs=maintenance_costs
        )
        for rank, pick in enumerate(result.picks, start=1):
            yield emit(pick, rank)
        n_sites, total_cost, total_value, solver_name = (
            len(result.picks),
            result.cost_usd,
            result.objective_value,
            "constrained_greedy",
        )
    else:
        yield StageEvent("solving", "Running CELF cost-effective greedy (E2)")
        last: Selection | None = None
        n_sites = 0
        for rank, pick in enumerate(solve(objective, costs, params.budget_usd), start=1):
            yield emit(pick, rank)
            last = pick
            n_sites = rank
        total_cost = last.cumulative_cost_usd if last else 0.0
        total_value = last.cumulative_value if last else 0.0
        solver_name = "celf"

    yield DoneEvent(solver=solver_name, n_sites=n_sites, total_cost_usd=total_cost, total_ewcb=total_value)
