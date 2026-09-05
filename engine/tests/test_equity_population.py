from __future__ import annotations

import pytest
from engine.equity.population import redistribute_population, summarize_unallocated_population
from engine.ingest import d04_osm, d07_census, d07b_tiger_bg
from engine.ingest.manifest import is_cached

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in (d04_osm, d07_census, d07b_tiger_bg)),
    reason="D4/D7/D7b not all ingested yet",
)


def test_redistribution_produces_real_buildings() -> None:
    b = redistribute_population()
    assert len(b) > 1000
    assert (b["population"] >= 0).all()
    assert (b["population"] <= b["population_uncapped"] + 1e-6).all()


def test_no_single_building_exceeds_plausible_density() -> None:
    from engine.equity.population import MAX_PERSONS_PER_M2_FLOOR_AREA

    b = redistribute_population()
    max_plausible = b["footprint_m2"] * b["floor_count"] * MAX_PERSONS_PER_M2_FLOOR_AREA
    assert (b["population"] <= max_plausible + 1e-6).all()


def test_unallocated_population_is_tracked_not_hidden() -> None:
    b = redistribute_population()
    summary = summarize_unallocated_population(b)
    assert len(summary) > 0
    # Every block group's allocated + unallocated must reconstruct its real ACS total.
    reconstructed = summary["allocated_population"] + summary["unallocated_population"]
    assert (abs(reconstructed - summary["block_group_population"]) < 1e-6).all()
