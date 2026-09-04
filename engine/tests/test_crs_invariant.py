"""The CRS invariant test (COOLBLOCK-BUILD-PLAN.md §5.1.3, §10 Phase 1).

"The strategy brief flags geospatial coordinate handling as the single place
LLM-written code fails silently. This test is the antidote and it gets
written in Phase 1, before any UI exists." Every ingest module reprojects
through engine.ingest.crs, never a one-off `.to_crs()` call -- so this test
covers the whole pipeline, not one function nobody else uses.

The landmark used here is a real vertex of a real parcel (APN 11624044,
1217 E McKinley St, Phoenix AZ), fetched live from the Maricopa County
Assessor's ArcGIS REST service during Phase 1 R3 verification -- not a
guessed coordinate.
"""

from __future__ import annotations

import geopandas as gpd
import pyproj
import pytest
from engine.config import load_neighborhood_config
from engine.ingest.crs import to_canonical_crs_vector
from shapely.geometry import Point

# Real vertex from parcel APN 11624044 (Maricopa County Assessor, fetched live).
LANDMARK_LON = -112.05556184554283
LANDMARK_LAT = 33.456684061633489

ROUND_TRIP_TOLERANCE_M = 1.0


def test_landmark_is_within_the_locked_bbox() -> None:
    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84
    assert bbox.min_lon <= LANDMARK_LON <= bbox.max_lon
    assert bbox.min_lat <= LANDMARK_LAT <= bbox.max_lat


def test_wgs84_utm_roundtrip_drift_under_one_metre() -> None:
    cfg = load_neighborhood_config()
    fwd = pyproj.Transformer.from_crs(cfg.wgs84_epsg, cfg.target_epsg, always_xy=True)
    inv = pyproj.Transformer.from_crs(cfg.target_epsg, cfg.wgs84_epsg, always_xy=True)

    x, y = fwd.transform(LANDMARK_LON, LANDMARK_LAT)
    lon2, lat2 = inv.transform(x, y)

    geod = pyproj.Geod(ellps="WGS84")
    _, _, drift_m = geod.inv(LANDMARK_LON, LANDMARK_LAT, lon2, lat2)
    assert drift_m < ROUND_TRIP_TOLERANCE_M


def test_to_canonical_crs_vector_matches_direct_transform() -> None:
    """The shared helper every ingest module calls must agree with a direct
    pyproj transform of the same point, within the same tolerance."""
    cfg = load_neighborhood_config()
    gdf = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(LANDMARK_LON, LANDMARK_LAT)], crs=f"EPSG:{cfg.wgs84_epsg}"
    )

    reprojected = to_canonical_crs_vector(gdf)
    assert reprojected.crs.to_epsg() == cfg.target_epsg

    fwd = pyproj.Transformer.from_crs(cfg.wgs84_epsg, cfg.target_epsg, always_xy=True)
    expected_x, expected_y = fwd.transform(LANDMARK_LON, LANDMARK_LAT)

    got = reprojected.geometry.iloc[0]
    drift_m = ((got.x - expected_x) ** 2 + (got.y - expected_y) ** 2) ** 0.5
    assert drift_m < ROUND_TRIP_TOLERANCE_M


def test_to_canonical_crs_vector_rejects_missing_crs() -> None:
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(LANDMARK_LON, LANDMARK_LAT)], crs=None)
    with pytest.raises(ValueError):
        to_canonical_crs_vector(gdf)
