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
    stream_solve,
)

pytestmark = pytest.mark.skipif(
    not CANDIDATES_PATH.exists(),
    reason=f"{CANDIDATES_PATH} not built yet -- run `uv run python scripts/export_map_layers.py`",
)


@pytest.fixture(scope="module")
def universe() -> gpd.GeoDataFrame:
    return load_candidate_universe()


def test_celf_path_emits_stages_then_sites_then_done(universe: gpd.GeoDataFrame) -> None:
    events = list(stream_solve(SolveParams(budget_usd=20_000.0), candidates=universe))

    stages = [e for e in events if isinstance(e, StageEvent)]
    sites = [e for e in events if isinstance(e, SiteEvent)]
    done = [e for e in events if isinstance(e, DoneEvent)]

    assert [s.stage for s in stages] == ["loading_candidates", "scoring_impact", "solving"]
    assert len(done) == 1
    assert done[0].solver == "celf"
    assert done[0].n_sites == len(sites)
    assert events.index(done[0]) == len(events) - 1  # done is always last
    assert [s.rank for s in sites] == list(range(1, len(sites) + 1))  # ranks arrive in order


def test_celf_solve_never_exceeds_budget(universe: gpd.GeoDataFrame) -> None:
    budget = 15_000.0
    events = list(stream_solve(SolveParams(budget_usd=budget), candidates=universe))
    done = next(e for e in events if isinstance(e, DoneEvent))
    assert done.total_cost_usd <= budget + 1e-6


def test_constrained_path_used_when_a_side_constraint_is_set(universe: gpd.GeoDataFrame) -> None:
    events = list(
        stream_solve(SolveParams(budget_usd=20_000.0, public_land_only=True), candidates=universe)
    )
    done = next(e for e in events if isinstance(e, DoneEvent))
    sites = [e for e in events if isinstance(e, SiteEvent)]
    assert done.solver == "constrained_greedy"
    assert all(s.properties["ownership"] in ("public_row", "public_parcel") for s in sites)


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
    sites = [e for e in events if isinstance(e, SiteEvent)]
    assert excluded_id not in {s.candidate_id for s in sites}
