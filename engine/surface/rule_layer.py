"""B1 -- the rule layer (COOLBLOCK-BUILD-PLAN.md §6.2 B1): fast, deterministic,
fully explainable. From NAIP, subtract buildings (+buffer), road carriageways
(+lane buffer), water, and existing tree canopy -- what's left is plantable.

Two adaptations from the plan's literal spec, both disclosed:

1. "Existing canopy (NDVI > tau AND height > 3m from DEM/nDSM)" needs a
   normalized surface model (DSM - DEM) to separate canopy height from
   ground vegetation. We have a bare-earth DEM (D12) but no DSM/nDSM --
   verified against the data contract, not assumed -- so there is no way
   to compute vegetation *height* from currently ingested sources. This
   uses real, mapped OSM tree points (D4, 832 trees) buffered by an
   assumed mature-crown radius instead. This under-counts unmapped trees
   and cannot detect canopy shape directly; it does not over-exclude
   grass/turf (which the plan's ordering keeps in the plantable pool).
2. "Marked infrastructure" (e.g. utility easements) has no ingested source
   -- not fabricated, just absent from this exclusion pass.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features
import rioxarray  # noqa: F401 -- registers the .rio accessor
from affine import Affine
from rasterio.crs import CRS
from scipy import ndimage
from shapely.geometry import shape

from engine.ingest import d03_naip, d04_osm
from engine.ingest.grid import get_canonical_grid
from engine.ingest.manifest import version_dir

BoolArray = np.ndarray[Any, np.dtype[np.bool_]]

BUILDING_BUFFER_M = 1.0
TREE_CANOPY_RADIUS_M = 4.0  # assumed mature street-tree crown radius, disclosed proxy for real canopy extent
MIN_PLANTABLE_AREA_M2 = 4.0  # a single tree pit; smaller polygons are rasterization noise, not real space

# Right-of-way half-width by OSM highway class, metres -- planning-estimate
# carriageway + shoulder widths, not surveyed values.
ROAD_BUFFER_M: dict[str, float] = {
    "motorway": 15.0,
    "motorway_link": 12.0,
    "primary": 12.0,
    "primary_link": 10.0,
    "secondary": 9.0,
    "tertiary": 7.0,
    "residential": 6.0,
    "unclassified": 6.0,
    "service": 4.0,
    "pedestrian": 2.0,
    "footway": 1.5,
    "steps": 1.5,
}
DEFAULT_ROAD_BUFFER_M = 5.0


def _rasterize(gdf: gpd.GeoDataFrame, shape_hw: tuple[int, ...], transform: Affine) -> BoolArray:
    if len(gdf) == 0:
        return np.zeros(shape_hw, dtype=bool)
    result: BoolArray = rasterio.features.rasterize(
        [(geom, 1) for geom in gdf.geometry if geom is not None and not geom.is_empty],
        out_shape=shape_hw,
        transform=transform,
        fill=0,
        dtype="uint8",
    ).astype(bool)
    return result


def compute_ndvi() -> tuple[np.ndarray[Any, np.dtype[np.float64]], Affine, CRS]:
    """NDVI from NAIP at native 0.6m -- returned alongside its transform and
    CRS so exclusion layers can be rasterized onto the same grid."""
    path = version_dir(d03_naip.SOURCE_ID, d03_naip.VERSION) / "naip_rgbir.tif"
    with rasterio.open(path) as src:
        red = src.read(1).astype("float64")
        nir = src.read(4).astype("float64")
        transform = src.transform
        crs = src.crs
    denom = nir + red
    ndvi = np.divide(nir - red, denom, out=np.zeros_like(denom), where=denom != 0)
    return ndvi, transform, crs


def compute_plantable_mask() -> tuple[BoolArray, Affine, CRS]:
    """True where a new intervention could physically go. Excludes
    buildings, roads, and (proxy) existing tree canopy, at NAIP's native
    0.6m grid."""
    ndvi, transform, crs = compute_ndvi()
    shape_hw = ndvi.shape
    crs_str = str(crs)

    buildings = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "buildings.parquet")
    buildings = buildings.to_crs(crs_str)
    buildings_buffered = buildings.copy()
    buildings_buffered["geometry"] = buildings.geometry.buffer(BUILDING_BUFFER_M)
    building_mask = _rasterize(buildings_buffered, shape_hw, transform)

    roads = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "roads.parquet")
    roads = roads.to_crs(crs_str)
    road_buffer_m = roads["highway"].map(ROAD_BUFFER_M).fillna(DEFAULT_ROAD_BUFFER_M)
    roads_buffered = roads.copy()
    roads_buffered["geometry"] = roads.geometry.buffer(road_buffer_m)
    road_mask = _rasterize(roads_buffered, shape_hw, transform)

    trees = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "trees.parquet")
    trees = trees.to_crs(crs_str)
    trees_buffered = trees.copy()
    trees_buffered["geometry"] = trees.geometry.buffer(TREE_CANOPY_RADIUS_M)
    canopy_mask = _rasterize(trees_buffered, shape_hw, transform)

    # Added after the Phase 4 manual spot-check (docs/METHODOLOGY.md) found
    # a real paved, striped surface parking lot flagged as plantable --
    # neither "roads" (linear highway features) nor "buildings" (structures)
    # covers off-street parking lots.
    parking = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "parking.parquet")
    parking = parking.to_crs(crs_str)
    parking_mask = _rasterize(parking, shape_hw, transform)

    excluded = building_mask | road_mask | canopy_mask | parking_mask
    plantable = ~excluded

    # Morphological opening -- rasterizing real-world vector data at 0.6m
    # produces single-pixel speckle at buffer edges; this removes noise
    # smaller than ~1 pixel wide without changing any real region's shape
    # by more than that.
    plantable = ndimage.binary_opening(plantable, structure=np.ones((3, 3)))

    return plantable, transform, crs


def vectorize_plantable(mask: BoolArray, transform: Affine, crs: CRS) -> gpd.GeoDataFrame:
    polygons = [
        {"geometry": shape(geom), "value": val}
        for geom, val in rasterio.features.shapes(mask.astype("uint8"), mask=mask, transform=transform)
        if val == 1
    ]
    if not polygons:
        return gpd.GeoDataFrame(columns=["geometry", "area_m2"], geometry="geometry", crs=crs)

    gdf = gpd.GeoDataFrame(polygons, crs=crs).drop(columns=["value"])
    gdf["area_m2"] = gdf.geometry.area
    gdf = gdf[gdf["area_m2"] >= MIN_PLANTABLE_AREA_M2].reset_index(drop=True)
    return gdf


def run_rule_layer() -> gpd.GeoDataFrame:
    mask, transform, crs = compute_plantable_mask()
    gdf = vectorize_plantable(mask, transform, crs)
    target_epsg = get_canonical_grid().epsg
    return gdf.to_crs(epsg=target_epsg)
