"""Smoke test for D4 (OSM/Overpass): shape, bounds, null rate, per layer."""

from __future__ import annotations

import pytest
from engine.ingest.d04_osm import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached
from engine.tests.ingest_helpers import assert_vector_smoke, load_cached_vector

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D4 not ingested yet -- run engine.ingest.d04_osm"
)

# buildings/roads/landuse/trees are dense in Edison-Eastlake; amenities (schools,
# playgrounds, bus stops) are legitimately sparse -- a handful is expected, not zero.
_MIN_ROWS = {"buildings": 500, "roads": 500, "landuse": 20, "trees": 50, "amenities": 1}


@pytest.mark.parametrize("layer", ["buildings", "roads", "landuse", "trees", "amenities"])
def test_smoke(layer: str) -> None:
    gdf = load_cached_vector(SOURCE_ID, VERSION, f"{layer}.parquet")
    assert_vector_smoke(
        gdf,
        required_columns=["geometry"],
        min_rows=_MIN_ROWS[layer],
        null_check_columns=["geometry"],
    )
