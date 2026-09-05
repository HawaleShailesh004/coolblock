"""C2 -- shade raytracing (COOLBLOCK-BUILD-PLAN.md §6.3 C2), "the visual
centrepiece": for each candidate, how many hours of the design day does its
shadow actually fall on real pedestrian space?

The design day is the real hottest day on record in the ingested Open-Meteo
series (D13, 2021-2025 summers) -- not an assumed date. For each hour
09:00-18:00 that day, real solar geometry (`pvlib.solarposition`) gives
sun azimuth/elevation at the neighborhood's centroid; each candidate's
assumed canopy/structure height and width casts a shadow whose reach and
direction follow directly from that geometry, and the shadow's footprint
is intersected against real pedestrian-surface vector data (OSM footways,
steps, pedestrian ways, bus stops, playgrounds, and school grounds).

Disclosed simplifications, all real limitations rather than invented ones:

1. **No full height-field/DEM occlusion.** The plan's step 2 ("Build a
   height field: DEM + building heights + existing canopy + proposed
   canopy") and step 3 ("cast shadows via GPU-style horizon-angle sweeping
   on the height raster") describe a full-neighborhood raster raytrace.
   This computes each candidate's *own* shadow reaching nearby pedestrian
   surfaces directly from solar geometry, without checking whether an
   intervening building would itself already shade (or block) that
   shadow first. A full z-buffer sweep is a natural upgrade path (the
   ingested DEM, D12, and building heights, `engine/surface/heights.py`,
   are both already available) but was not built this phase given time.
2. **One representative crown/structure per candidate, not per planted
   tree.** A `park_lot_tree_cluster` candidate's shadow is modeled as a
   single mature tree's crown centered at the candidate polygon's
   centroid -- consistent with C1's same simplification
   (`engine/impact/cooling_kernel.py`) -- not `capacity` separate shadows.
3. **Assumed, disclosed dimensions**, since OSM carries no tree-height or
   shade-structure-height tags for un-built candidates: a mature street
   tree is modeled at `MATURE_TREE_HEIGHT_M` = 8m (roughly matching the
   crown diameter already assumed in `engine.surface.rule_layer`'s
   4m-radius crown proxy) with crown width = 2 * that radius; a shade
   structure is modeled at `SHADE_STRUCTURE_HEIGHT_M` = 3m (typical bus
   shelter canopy height) with `SHADE_STRUCTURE_WIDTH_M` = 3m footprint.
4. **No "school route" network.** No walking-route data exists in the OSM
   extract for this bbox (school routes would need route relations that
   are not mapped here) -- school *grounds* (the `amenity=school`
   polygon/point, buffered) stand in as a proxy for school-adjacent
   pedestrian space, disclosed as narrower than the plan's literal
   "school walking routes."
5. **Long, low-angle shadows are capped** at `MAX_SHADOW_LENGTH_M` (60m).
   Near sunrise/sunset a physically correct shadow can stretch hundreds of
   metres, but modeling it as a constant-width rectangle that far from its
   source stops being a meaningful approximation of a real tree's dappled,
   foreshortened shadow -- capped rather than reported as a literal
   60m+ shade claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import pvlib

from engine.config import load_neighborhood_config
from engine.ingest import d04_osm, d13_open_meteo
from engine.ingest.manifest import version_dir
from engine.surface.rule_layer import TREE_CANOPY_RADIUS_M

DESIGN_DAY_START_HOUR = 9
DESIGN_DAY_END_HOUR = 18  # inclusive

MATURE_TREE_HEIGHT_M = 8.0
TREE_CROWN_WIDTH_M = 2.0 * TREE_CANOPY_RADIUS_M

SHADE_STRUCTURE_HEIGHT_M = 3.0
SHADE_STRUCTURE_WIDTH_M = 3.0

MAX_SHADOW_LENGTH_M = 60.0

PEDESTRIAN_HIGHWAY_TYPES = {"footway", "steps", "pedestrian"}
BUS_STOP_BUFFER_M = 3.0
SCHOOL_GROUNDS_BUFFER_M = 15.0

CANOPY_INTERVENTION_TYPES = {"street_tree", "park_lot_tree_cluster"}
SHADE_STRUCTURE_INTERVENTION_TYPE = "shade_structure"


@dataclass(frozen=True)
class DesignDay:
    date: pd.Timestamp
    max_temperature_c: float
    hours: pd.DatetimeIndex  # tz-aware, 09:00-18:00 local


def find_design_day() -> DesignDay:
    """The real hottest day on record in the ingested Open-Meteo series --
    not an assumed date (COOLBLOCK-BUILD-PLAN.md §6.3 C2)."""
    df = pd.read_parquet(version_dir(d13_open_meteo.SOURCE_ID, d13_open_meteo.VERSION) / "hourly_summer_2021_2025.parquet")
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.date

    daily_max = df.groupby("date")["temperature_2m"].max()
    hottest_date = daily_max.idxmax()
    max_temp = float(daily_max.loc[hottest_date])

    cfg = load_neighborhood_config()
    hours = pd.date_range(
        start=pd.Timestamp(hottest_date).replace(hour=DESIGN_DAY_START_HOUR),
        end=pd.Timestamp(hottest_date).replace(hour=DESIGN_DAY_END_HOUR),
        freq="1h",
        tz=cfg.timezone_iana,
    )
    return DesignDay(date=pd.Timestamp(hottest_date), max_temperature_c=max_temp, hours=hours)


def solar_positions(design_day: DesignDay) -> pd.DataFrame:
    """Real solar azimuth/elevation per hour at the neighborhood centroid."""
    cfg = load_neighborhood_config()
    b = cfg.bbox_wgs84
    lat, lon = (b.min_lat + b.max_lat) / 2, (b.min_lon + b.max_lon) / 2
    return pvlib.solarposition.get_solarposition(design_day.hours, lat, lon)


def load_pedestrian_surfaces(crs: str) -> gpd.GeoDataFrame:
    """Real pedestrian-surface vector data: sidewalks/footways, crosswalks,
    bus stops, playgrounds, and school grounds (see module docstring,
    disclosed simplification 4, for "school routes")."""
    roads = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "roads.parquet").to_crs(crs)
    footways = roads[roads["highway"].isin(PEDESTRIAN_HIGHWAY_TYPES)][["geometry"]].copy()
    footways["surface_type"] = "sidewalk_or_crossing"

    amenities = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "amenities.parquet").to_crs(crs)

    bus_stops = amenities[amenities.get("highway") == "bus_stop"][["geometry"]].copy()
    bus_stops["geometry"] = bus_stops.geometry.buffer(BUS_STOP_BUFFER_M)
    bus_stops["surface_type"] = "bus_stop"

    playgrounds = amenities[amenities.get("leisure") == "playground"][["geometry"]].copy()
    playgrounds["surface_type"] = "playground"

    schools = amenities[amenities.get("amenity") == "school"][["geometry"]].copy()
    schools["geometry"] = schools.geometry.buffer(SCHOOL_GROUNDS_BUFFER_M)
    schools["surface_type"] = "school_grounds"

    parts = [gdf for gdf in (footways, bus_stops, playgrounds, schools) if len(gdf) > 0]
    combined = pd.concat(parts, ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs=crs)


def _height_and_width(intervention_type: str) -> tuple[float, float]:
    if intervention_type == SHADE_STRUCTURE_INTERVENTION_TYPE:
        return SHADE_STRUCTURE_HEIGHT_M, SHADE_STRUCTURE_WIDTH_M
    return MATURE_TREE_HEIGHT_M, TREE_CROWN_WIDTH_M


def _shadow_polygon(center: Any, height_m: float, width_m: float, azimuth_deg: float, elevation_deg: float) -> Any | None:
    """A rectangle approximating a shadow: `height_m / tan(elevation)` long
    (capped), `width_m` wide, pointing away from the sun. `None` if the sun
    is at or below the horizon."""
    from shapely.affinity import rotate
    from shapely.geometry import box

    if elevation_deg <= 0:
        return None

    shadow_length_m = min(height_m / np.tan(np.radians(elevation_deg)), MAX_SHADOW_LENGTH_M)
    if shadow_length_m <= 0:
        return None

    # Shadow azimuth points opposite the sun. Build the rectangle running
    # along +y from the origin, then rotate to the shadow's compass bearing
    # (shapely's rotate is counterclockwise from +x; compass bearing is
    # clockwise from north/+y) and translate to the candidate's centroid.
    rect = box(-width_m / 2.0, 0.0, width_m / 2.0, shadow_length_m)
    shadow_azimuth_deg = (azimuth_deg + 180.0) % 360.0
    rotated = rotate(rect, -shadow_azimuth_deg, origin=(0, 0))
    from shapely.affinity import translate

    return translate(rotated, xoff=center.x, yoff=center.y)


def compute_shade_hours(
    candidates: gpd.GeoDataFrame,
    pedestrian_surfaces: gpd.GeoDataFrame,
    sun_positions: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Adds `shade_hours_delivered` to `candidates`: how many of the design
    day's 09:00-18:00 hourly steps this candidate's shadow intersects real
    pedestrian surfaces."""
    sindex = pedestrian_surfaces.sindex

    shade_hours = np.zeros(len(candidates), dtype="float64")
    for i, row in enumerate(candidates.itertuples()):
        height_m, width_m = _height_and_width(row.intervention_type)
        center = row.geometry.centroid

        hours_shaded = 0
        for _, sun in sun_positions.iterrows():
            shadow = _shadow_polygon(center, height_m, width_m, sun["azimuth"], sun["apparent_elevation"])
            if shadow is None:
                continue
            candidate_idx = list(sindex.query(shadow, predicate="intersects"))
            if candidate_idx and pedestrian_surfaces.iloc[candidate_idx].intersects(shadow).any():
                hours_shaded += 1

        shade_hours[i] = float(hours_shaded)

    out = candidates.copy()
    out["shade_hours_delivered"] = shade_hours
    return out


def run_shade_raytrace(candidates: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, DesignDay]:
    """C2's full output: candidates with `shade_hours_delivered`, plus the
    design day used, so any downstream report can state which real day the
    number is computed for."""
    design_day = find_design_day()
    sun_positions = solar_positions(design_day)
    pedestrian_surfaces = load_pedestrian_surfaces(str(candidates.crs))
    scored = compute_shade_hours(candidates, pedestrian_surfaces, sun_positions)
    return scored, design_day
