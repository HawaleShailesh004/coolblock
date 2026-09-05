from __future__ import annotations

import pytest
from engine.ingest import d03_naip, d04_osm
from engine.ingest.manifest import is_cached
from engine.surface.rule_layer import MIN_PLANTABLE_AREA_M2, run_rule_layer

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in (d03_naip, d04_osm)),
    reason="D3/D4 not ingested yet",
)


def test_rule_layer_produces_real_polygons() -> None:
    gdf = run_rule_layer()
    assert len(gdf) > 100
    assert (gdf["area_m2"] >= MIN_PLANTABLE_AREA_M2).all()
    assert gdf.crs is not None


def test_plantable_area_is_a_plausible_fraction_of_the_neighborhood() -> None:
    from engine.ingest.grid import get_canonical_grid

    gdf = run_rule_layer()
    grid = get_canonical_grid()
    minx, miny, maxx, maxy = grid.bounds
    total_area = (maxx - minx) * (maxy - miny)

    plantable_fraction = gdf["area_m2"].sum() / total_area
    # Verified against real NAIP imagery during Phase 4: dense-urban Phoenix
    # residential parcels carry a lot of bare desert-landscaped yard, so
    # this is a wide plausibility band, not a tight one.
    assert 0.1 < plantable_fraction < 0.9


def test_plantable_polygons_do_not_overlap_parking_lots() -> None:
    import geopandas as gpd
    from engine.ingest.manifest import version_dir

    gdf = run_rule_layer()
    parking = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "parking.parquet").to_crs(
        gdf.crs
    )
    if len(parking) == 0:
        pytest.skip("no parking polygons in this bbox")

    # The *actual* intersection geometry, not sjoin's preserved left-geometry
    # (which would report the whole plantable polygon's area for any match).
    intersection = gpd.overlay(gdf[["geometry"]], parking[["geometry"]], how="intersection")
    overlap_area = intersection.geometry.area.sum() if len(intersection) else 0.0
    # Buffer/rasterization edge effects can produce a sliver of overlap;
    # there should be no *substantial* double-counted area.
    assert overlap_area < 0.05 * gdf["area_m2"].sum()
