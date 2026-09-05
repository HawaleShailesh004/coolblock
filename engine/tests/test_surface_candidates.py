from __future__ import annotations

import pytest
from engine.ingest import d03_naip, d04_osm, d06_parcels
from engine.ingest.manifest import is_cached
from engine.surface.candidates import generate_candidates

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in (d03_naip, d04_osm, d06_parcels)),
    reason="D3/D4/D6 not all ingested yet",
)


def test_candidates_have_required_fields() -> None:
    gdf = generate_candidates()
    assert len(gdf) > 100
    for col in ("candidate_id", "area_m2", "ownership", "intervention_type", "capacity", "total_cost_usd"):
        assert col in gdf.columns

    assert gdf["candidate_id"].is_unique
    assert (gdf["capacity"] > 0).all()
    assert (gdf["total_cost_usd"] > 0).all()
    assert set(gdf["ownership"].unique()) <= {"public_row", "public_parcel", "private"}


def test_capacity_matches_area_and_spacing() -> None:
    from engine.surface.candidates import STREET_TREE_SPACING_M, TREE_CLUSTER_SPACING_M

    gdf = generate_candidates()
    street_trees = gdf[gdf["intervention_type"] == "street_tree"]
    clusters = gdf[gdf["intervention_type"] == "park_lot_tree_cluster"]

    if len(street_trees) > 0:
        max_expected = (street_trees["area_m2"] // (STREET_TREE_SPACING_M**2)).clip(lower=1)
        assert (street_trees["capacity"] <= max_expected + 1).all()
    if len(clusters) > 0:
        max_expected = clusters["area_m2"] // (TREE_CLUSTER_SPACING_M**2)
        assert (clusters["capacity"] <= max_expected + 1).all()


def test_total_cost_is_consistent() -> None:
    gdf = generate_candidates()
    computed = gdf["capacity"] * gdf["unit_cost_usd"]
    assert (abs(gdf["total_cost_usd"] - computed) < 1e-6).all()
