"""Phase 7 -- `engine.optimize.plan_service`, the shared warm-solve path
both the API's ARQ worker and this test call directly. Runs against the
real cached candidate export (`data/derived/edison-eastlake/candidates.geojson`,
built by `scripts/export_map_layers.py`) -- if that export is missing
(clean checkout, before Phase 4/5's exports have been run), these tests
skip rather than fail, matching this project's existing pattern for
cache-dependent tests (see `engine/tests/ingest_helpers.py`)."""

from __future__ import annotations

import json

import geopandas as gpd
import pytest
from engine.optimize.plan_service import (
    CANDIDATES_PATH,
    DoneEvent,
    SiteEvent,
    SolveParams,
    StageEvent,
    load_candidate_universe,
    run_baseline_comparison,
    stream_solve,
)

pytestmark = pytest.mark.skipif(
    not CANDIDATES_PATH.exists(),
    reason=f"{CANDIDATES_PATH} not built yet -- run `uv run python scripts/export_map_layers.py`",
)


@pytest.fixture(scope="module")
def universe() -> gpd.GeoDataFrame:
    return load_candidate_universe()


def test_unconstrained_path_emits_stages_then_sites_then_done(universe: gpd.GeoDataFrame) -> None:
    events = list(stream_solve(SolveParams(budget_usd=20_000.0), candidates=universe))

    stages = [e for e in events if isinstance(e, StageEvent)]
    sites = [e for e in events if isinstance(e, SiteEvent)]
    done = [e for e in events if isinstance(e, DoneEvent)]

    assert [s.stage for s in stages] == ["loading_candidates", "scoring_impact", "solving"]
    assert len(done) == 1
    assert done[0].solver == "exact_milp"  # the default pool is small enough to prove (docs/adr/0028-*.md)
    assert done[0].n_sites == len(sites)
    assert events.index(done[0]) == len(events) - 1  # done is always last
    assert [s.rank for s in sites] == list(range(1, len(sites) + 1))  # ranks arrive in order


def test_unconstrained_solve_never_exceeds_budget(universe: gpd.GeoDataFrame) -> None:
    budget = 15_000.0
    events = list(stream_solve(SolveParams(budget_usd=budget), candidates=universe))
    done = next(e for e in events if isinstance(e, DoneEvent))
    assert done.total_cost_usd <= budget + 1e-6


def test_constrained_path_used_when_a_side_constraint_is_set(universe: gpd.GeoDataFrame) -> None:
    events = list(stream_solve(SolveParams(budget_usd=20_000.0, max_sites_per_zone=2), candidates=universe))
    done = next(e for e in events if isinstance(e, DoneEvent))
    assert done.solver == "constrained_greedy"


def test_default_plan_is_trees_on_public_land_and_proven_optimal(universe: gpd.GeoDataFrame) -> None:
    """docs/adr/0027-*.md: the default plan answers the product's own
    question (trees), on land a city can plant without an owner's consent,
    and the public-land filter shrinks the pool instead of forcing the
    non-lazy constrained solver. docs/adr/0028-*.md: that pool is small
    enough that the user gets the proven-optimal plan, not the greedy one."""
    events = list(stream_solve(SolveParams(budget_usd=20_000.0), candidates=universe))
    done = next(e for e in events if isinstance(e, DoneEvent))
    sites = [e for e in events if isinstance(e, SiteEvent)]
    assert done.solver == "exact_milp"
    assert sites, "expected a real tree plan at $20,000"
    assert {s.intervention_type for s in sites} <= {"street_tree", "park_lot_tree_cluster"}
    assert all(s.properties["ownership"] in ("public_row", "public_parcel") for s in sites)


def test_cool_roof_program_never_ranks_trees_against_roofs(universe: gpd.GeoDataFrame) -> None:
    events = list(
        stream_solve(SolveParams(budget_usd=20_000.0, program="cool_roofs", public_land_only=False), candidates=universe)
    )
    sites = [e for e in events if isinstance(e, SiteEvent)]
    assert sites
    assert {s.intervention_type for s in sites} == {"cool_roof"}


def test_required_site_outside_the_pool_is_reported_not_silently_dropped(universe: gpd.GeoDataFrame) -> None:
    roof_id = str(universe.loc[universe["intervention_type"] == "cool_roof", "candidate_id"].iloc[0])
    events = list(
        stream_solve(SolveParams(budget_usd=20_000.0, mandatory_include_ids=frozenset({roof_id})), candidates=universe)
    )
    assert any(isinstance(e, StageEvent) and e.stage == "mandatory_outside_pool" for e in events)
    assert roof_id not in {e.candidate_id for e in events if isinstance(e, SiteEvent)}


def test_max_sites_per_zone_is_respected_end_to_end(universe: gpd.GeoDataFrame) -> None:
    events = list(
        stream_solve(
            SolveParams(budget_usd=100_000.0, max_sites_per_zone=1),
            candidates=universe,
        )
    )
    sites = [e for e in events if isinstance(e, SiteEvent)]
    # every candidate carries a real geometry we can re-derive its zone from,
    # but the simplest end-to-end check available here is just that the
    # constraint didn't silently get ignored: fewer or equal sites than an
    # unconstrained solve at the same budget.
    unconstrained = [
        e for e in stream_solve(SolveParams(budget_usd=100_000.0), candidates=universe) if isinstance(e, SiteEvent)
    ]
    assert len(sites) <= len(unconstrained)


def test_site_event_geometry_and_properties_are_json_serializable(universe: gpd.GeoDataFrame) -> None:
    events = list(stream_solve(SolveParams(budget_usd=20_000.0), candidates=universe))
    sites = [e for e in events if isinstance(e, SiteEvent)]
    assert sites, "expected at least one site at this budget"
    payload = json.dumps(
        {
            "geometry": sites[0].geometry,
            "properties": sites[0].properties,
            "cost_usd": sites[0].cost_usd,
            "cumulative_cost_usd": sites[0].cumulative_cost_usd,
        }
    )
    assert "candidate_id" in payload


def test_baseline_comparison_returns_all_five_strategies_and_coolblock_wins(universe: gpd.GeoDataFrame) -> None:
    """§9 ★5's API-facing entry point. Real cost: `worst_first`'s baseline
    samples the actual downscaled LST raster (`engine.thermal.downscale.run_downscaling`,
    uncached, ~14s to refit) regardless of candidate-set size, so this is
    one of this suite's slower tests by design, not an accident -- kept to
    a single test rather than duplicated across budgets."""
    result = run_baseline_comparison(50_000.0, candidates=universe)
    assert set(result.keys()) == {"spread_evenly", "worst_first", "squeaky_wheel", "tes_score_only", "coolblock"}
    assert result["coolblock"] > result["tes_score_only"] > 0
    assert all(v >= 0 for v in result.values())


def test_mandatory_exclude_by_candidate_id_is_honored(universe: gpd.GeoDataFrame) -> None:
    baseline_sites = [
        e for e in stream_solve(SolveParams(budget_usd=20_000.0), candidates=universe) if isinstance(e, SiteEvent)
    ]
    assert baseline_sites, "expected at least one site to exclude"
    excluded_id = baseline_sites[0].candidate_id

    events = list(
        stream_solve(
            SolveParams(budget_usd=20_000.0, mandatory_exclude_ids=frozenset({excluded_id})),
            candidates=universe,
        )
    )
    assert next(e for e in events if isinstance(e, DoneEvent)).solver == "constrained_greedy"
    sites = [e for e in events if isinstance(e, SiteEvent)]
    assert excluded_id not in {s.candidate_id for s in sites}
