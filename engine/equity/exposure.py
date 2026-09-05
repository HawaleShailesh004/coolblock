"""D3 -- exposure weighting (COOLBLOCK-BUILD-PLAN.md §6.4 D3).

People are not uniformly exposed to outdoor heat. This computes a
per-building exposure multiplier -- 1.0 baseline, multiplied up for real
OSM-derived proximity to bus stops (transit riders wait outdoors,
unshaded, for a variable amount of time) and schools (children walk to
and from them on foot) within `EXPOSURE_RADIUS_M`.

Disclosed, exactly as the plan's own phrasing anticipates
("exposure multipliers derived from OSM features," not from demographic
microdata this project does not have):

1. **No outdoor-worker exposure.** No ingested source identifies outdoor
   workplaces (construction sites, agricultural land, delivery routes) in
   this bbox -- omitted rather than faked with an invented proxy.
2. **The multipliers are planning judgments, not fitted effect sizes.**
   `BUS_STOP_EXPOSURE_MULTIPLIER` and `SCHOOL_EXPOSURE_MULTIPLIER` express
   "somewhat more heat-exposed than a building with neither nearby," not a
   measured behavioral effect from ridership or enrollment data -- no such
   data is ingested for this neighborhood.
3. **Proximity is a population-wide proxy, not a survey.** A building
   near a bus stop does not mean its residents ride transit; a building
   near a school does not mean its residents walk children there. This is
   the same kind of disclosed simplification as D1's area-weighted
   population redistribution -- a reasonable proxy from the data actually
   available, not a claim of individual-level accuracy.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np

from engine.ingest import d04_osm
from engine.ingest.manifest import version_dir

EXPOSURE_RADIUS_M = 400.0  # ~5-minute walk -- standard transit-catchment planning radius
BUS_STOP_EXPOSURE_MULTIPLIER = 1.3
SCHOOL_EXPOSURE_MULTIPLIER = 1.2


def _near_any(
    points: gpd.GeoSeries, geoms: gpd.GeoSeries, distance_m: float
) -> np.ndarray[Any, np.dtype[np.bool_]]:
    if len(geoms) == 0:
        return np.zeros(len(points), dtype=bool)
    sindex = geoms.sindex
    result = np.zeros(len(points), dtype=bool)
    for i, geom in enumerate(points):
        buffered = geom.buffer(distance_m)
        result[i] = len(sindex.query(buffered, predicate="intersects")) > 0
    return result


def compute_exposure_multiplier(buildings: gpd.GeoDataFrame) -> np.ndarray[Any, np.dtype[np.float64]]:
    """One exposure multiplier per row of `buildings` (uses its geometry
    centroid), from real proximity to bus stops and schools."""
    amenities = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "amenities.parquet").to_crs(
        buildings.crs
    )
    bus_stops = amenities[amenities.get("highway") == "bus_stop"]
    schools = amenities[amenities.get("amenity") == "school"]

    centroids = buildings.geometry.centroid
    near_bus = _near_any(centroids, bus_stops.geometry, EXPOSURE_RADIUS_M)
    near_school = _near_any(centroids, schools.geometry, EXPOSURE_RADIUS_M)

    exposure = np.ones(len(buildings), dtype="float64")
    exposure = np.where(near_bus, exposure * BUS_STOP_EXPOSURE_MULTIPLIER, exposure)
    exposure = np.where(near_school, exposure * SCHOOL_EXPOSURE_MULTIPLIER, exposure)
    return exposure
