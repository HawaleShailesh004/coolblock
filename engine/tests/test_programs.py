"""engine.optimize.programs -- the candidate pools that keep trees and cool
roofs from being ranked against each other (docs/adr/0027-*.md). Pure
logic on a tiny synthetic frame; no cached data needed."""

from __future__ import annotations

import geopandas as gpd
import pytest
from engine.optimize.programs import DEFAULT_PROGRAM, DEFAULT_PUBLIC_LAND_ONLY, candidate_pool
from shapely.geometry import Point


def _universe() -> gpd.GeoDataFrame:
    rows = [
        ("t-public", "street_tree", "public_row"),
        ("t-private", "park_lot_tree_cluster", "private"),
        ("r-public", "cool_roof", "public_parcel"),
        ("r-private", "cool_roof", "private"),
        ("pave", "cool_pavement", "public_parcel"),
        ("shade", "shade_structure", "public_row"),
    ]
    return gpd.GeoDataFrame(
        {
            "candidate_id": [r[0] for r in rows],
            "intervention_type": [r[1] for r in rows],
            "ownership": [r[2] for r in rows],
        },
        geometry=[Point(i, i) for i in range(len(rows))],
        crs="EPSG:32612",
    )


def test_default_is_trees_on_public_land() -> None:
    assert (DEFAULT_PROGRAM, DEFAULT_PUBLIC_LAND_ONLY) == ("trees", True)
    assert candidate_pool(_universe())["candidate_id"].tolist() == ["t-public"]


def test_programs_never_mix_intervention_families() -> None:
    trees = candidate_pool(_universe(), "trees", public_land_only=False)
    roofs = candidate_pool(_universe(), "cool_roofs", public_land_only=False)
    assert trees["candidate_id"].tolist() == ["t-public", "t-private"]
    assert roofs["candidate_id"].tolist() == ["r-public", "r-private"]


def test_zero_benefit_types_are_in_no_pool() -> None:
    """cool_pavement/shade_structure carry no population benefit under the
    objective; leaving them in a pool would only let a baseline waste
    budget on them and flatter the comparison."""
    for program in ("trees", "cool_roofs"):
        pool = candidate_pool(_universe(), program, public_land_only=False)
        assert not set(pool["intervention_type"]) & {"cool_pavement", "shade_structure"}


def test_pool_is_reindexed_from_zero() -> None:
    assert candidate_pool(_universe(), "cool_roofs", public_land_only=False).index.tolist() == [0, 1]


def test_unknown_program_is_an_error_not_a_silent_mixed_ranking() -> None:
    with pytest.raises(ValueError, match="unknown program"):
        candidate_pool(_universe(), "everything")
