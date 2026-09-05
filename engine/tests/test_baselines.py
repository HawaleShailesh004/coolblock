from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from engine.impact.albedo import run_albedo_model
from engine.impact.cooling_kernel import run_cooling_kernel
from engine.ingest import (
    d01_landsat,
    d02_sentinel2,
    d04_osm,
    d07_census,
    d07b_tiger_bg,
    d10_tree_equity_score,
    d11_nlcd,
)
from engine.ingest.manifest import is_cached
from engine.optimize.baselines import (
    assign_block_group,
    assign_tes_score,
    run_all_baselines,
    spread_evenly,
    squeaky_wheel,
    tes_score_only,
    worst_first,
)
from engine.optimize.objective import build_coverage_objective
from engine.surface.candidates import generate_candidates
from engine.surface.impervious_candidates import generate_impervious_candidates

_REQUIRED_SOURCES = (d01_landsat, d02_sentinel2, d04_osm, d07_census, d07b_tiger_bg, d10_tree_equity_score, d11_nlcd)

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in _REQUIRED_SOURCES),
    reason="not all required sources ingested yet",
)


def _real_scored_candidates() -> gpd.GeoDataFrame:
    tree_scored, _ = run_cooling_kernel(generate_candidates())
    imp_scored, _, _ = run_albedo_model(generate_impervious_candidates())
    combined = pd.concat([tree_scored, imp_scored], ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs=tree_scored.crs)


def test_assign_block_group_matches_real_d7b_coverage() -> None:
    """D7b's polygons spatially tile the whole study bbox with no gaps
    (unlike the separate 18-of-23 ACS-attribute join coverage noted in
    docs/adr/0006-*.md, which is about matching D7b's GEOIDs to D7's ACS
    records, not about spatial coverage of the bbox itself) -- every real
    candidate, being inside the bbox by construction, should fall within
    some D7b block group."""
    candidates = _real_scored_candidates()
    block_group = assign_block_group(candidates)
    assert block_group.notna().mean() == pytest.approx(1.0)


def test_assign_tes_score_is_within_the_real_published_range() -> None:
    candidates = _real_scored_candidates()
    tes = assign_tes_score(candidates)
    matched = tes.dropna()
    assert len(matched) > 0
    assert matched.between(0, 100).all()


def test_baseline_selections_never_exceed_budget() -> None:
    candidates = _real_scored_candidates()
    costs = candidates["total_cost_usd"].to_numpy()
    budget = 50_000.0

    for selection in (
        spread_evenly(candidates, costs, budget),
        worst_first(candidates, costs, budget),
        squeaky_wheel(candidates, costs, budget),
        tes_score_only(candidates, costs, budget),
    ):
        assert sum(costs[i] for i in selection) <= budget + 1e-6


def test_coolblock_beats_every_baseline_at_equal_budget() -> None:
    """The Phase 6 DoD's actual proof-of-work test (COOLBLOCK-BUILD-PLAN.md
    §6.5 E5): 'if CoolBlock does not beat TES-score-only by a clear
    margin, we have not built anything.' Checked against real candidates
    and real Census/TES data, not a synthetic instance."""
    candidates = _real_scored_candidates()
    objective = build_coverage_objective(candidates)
    costs = candidates["total_cost_usd"].to_numpy()

    results = run_all_baselines(candidates, objective, costs, budget_usd=50_000.0)
    coolblock_value = results["coolblock"]

    for name, value in results.items():
        if name == "coolblock":
            continue
        assert coolblock_value >= value, f"CoolBlock ({coolblock_value}) did not beat {name} ({value})"

    assert coolblock_value > results["tes_score_only"] * 1.05  # a "clear margin," not a coin flip
