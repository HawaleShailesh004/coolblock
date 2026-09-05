"""A3 -- the go/no-go validation gate (COOLBLOCK-BUILD-PLAN.md §6.1 A3).

Three independent checks:
1. Correlate the composite against Open-Meteo station air temperature.
2. Confirm known asphalt/parking-lot polygons read hotter than known park
   polygons by a physically plausible margin.
3. Confirm the surface reproduces hot spots the city already names in its
   published plans (Phoenix's own 2024 Shade Phoenix Plan, D15).

If this fails, §1.4's honesty rail applies: the product's language
downgrades from "predicted cooling" to "prioritization score" everywhere,
recorded in docs/METHODOLOGY.md in the same commit as the code that made
the call.
"""

from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry.base import BaseGeometry

from engine.config import load_neighborhood_config
from engine.ingest import d04_osm, d13_open_meteo, d15_phoenix_open_data
from engine.ingest.manifest import version_dir
from engine.thermal.composite import clear_sky_mask, load_landsat_cube, lst_celsius
from engine.thermal.downscale import DownscalingResult


@dataclass(frozen=True)
class StationCorrelationResult:
    pearson_r: float
    n_scenes: int
    mean_lst_minus_air_c: float  # LST always reads hotter than air temp for a sunny urban scene


@dataclass(frozen=True)
class LandcoverContrastResult:
    parking_mean_c: float
    park_mean_c: float
    contrast_c: float  # parking - park; should be positive and physically plausible
    n_parking_polygons: int
    n_park_polygons: int


@dataclass(frozen=True)
class CityHotspotResult:
    spearman_rho: float
    n_tracts: int
    our_tract_means_c: dict[str, float]
    city_tract_means_c: dict[str, float]


@dataclass(frozen=True)
class ValidationVerdict:
    station: StationCorrelationResult
    landcover: LandcoverContrastResult
    hotspot: CityHotspotResult
    passed: bool
    reasons: list[str]


# Go/no-go thresholds -- each one a physically-motivated minimum, not a
# number picked to make the gate pass.
MIN_STATION_CORRELATION = 0.3
MIN_LANDCOVER_CONTRAST_C = 0.5
MIN_HOTSPOT_CORRELATION = 0.3


def check_station_correlation() -> StationCorrelationResult:
    """Per-scene LST at the neighborhood centroid vs. Open-Meteo air
    temperature at the nearest local hour to that scene's acquisition."""
    ds = load_landsat_cube()
    mask = clear_sky_mask(ds["qa_pixel"])
    st = lst_celsius(ds["lwir11"]).where(mask & (ds["lwir11"] > 0))

    cfg = load_neighborhood_config()
    cy, cx = st.sizes["y"] // 2, st.sizes["x"] // 2
    centroid_lst = st.isel(y=cy, x=cx)

    meteo_path = version_dir(d13_open_meteo.SOURCE_ID, d13_open_meteo.VERSION) / "hourly_summer_2021_2025.parquet"
    meteo = pd.read_parquet(meteo_path)
    meteo["time"] = pd.to_datetime(meteo["time"])
    meteo = meteo.set_index("time").sort_index()

    tz = ZoneInfo(cfg.timezone_iana)
    pairs: list[tuple[float, float]] = []
    for t in centroid_lst["time"].values:
        lst_val = float(centroid_lst.sel(time=t))
        if not np.isfinite(lst_val):
            continue
        scene_time_local = pd.Timestamp(t, tz="UTC").tz_convert(tz).tz_localize(None)
        idx = meteo.index.get_indexer([scene_time_local], method="nearest")[0]
        if idx == -1:
            continue
        air_temp = float(meteo.iloc[idx]["temperature_2m"])
        pairs.append((lst_val, air_temp))

    arr = np.array(pairs)
    r = float(np.corrcoef(arr[:, 0], arr[:, 1])[0, 1]) if len(arr) > 2 else float("nan")
    mean_diff = float(np.mean(arr[:, 0] - arr[:, 1])) if len(arr) > 0 else float("nan")
    return StationCorrelationResult(pearson_r=r, n_scenes=len(arr), mean_lst_minus_air_c=mean_diff)


def _zonal_mean(raster: xr.DataArray, geom: BaseGeometry, crs: str) -> float:
    clipped = raster.rio.clip([geom], crs, drop=True, all_touched=True)
    vals = clipped.values
    valid = vals[np.isfinite(vals)]
    return float(valid.mean()) if valid.size else float("nan")


def check_landcover_contrast(downscaling: DownscalingResult) -> LandcoverContrastResult:
    """Parking-lot polygons should read hotter than park/grass polygons.

    Caveat found during Phase 3 (kept here, not hidden): of the 10
    OSM `amenity=parking` polygons in this bbox, several carry
    `building:levels` of 4-7 -- these are multi-storey parking
    *structures*, not open asphalt lots, so this samples rooftop
    temperature rather than pavement temperature. See
    notebooks/01-thermal-validation.ipynb and docs/METHODOLOGY.md for the
    resulting go/no-go call.
    """
    lst = downscaling.lst_10m

    buildings = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "buildings.parquet")
    landuse = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "landuse.parquet")

    parking = buildings[buildings.get("amenity") == "parking"]
    park = landuse[landuse.get("landuse").isin(["grass", "village_green"])]

    crs = f"EPSG:{load_neighborhood_config().target_epsg}"
    parking_means = [_zonal_mean(lst, geom, crs) for geom in parking.geometry]
    park_means = [_zonal_mean(lst, geom, crs) for geom in park.geometry]
    parking_means = [v for v in parking_means if np.isfinite(v)]
    park_means = [v for v in park_means if np.isfinite(v)]

    parking_mean = float(np.mean(parking_means)) if parking_means else float("nan")
    park_mean = float(np.mean(park_means)) if park_means else float("nan")
    return LandcoverContrastResult(
        parking_mean_c=parking_mean,
        park_mean_c=park_mean,
        contrast_c=parking_mean - park_mean,
        n_parking_polygons=len(parking_means),
        n_park_polygons=len(park_means),
    )


def check_city_hotspots(downscaling: DownscalingResult) -> CityHotspotResult:
    """Tract-mean LST vs. Phoenix's own published tract-mean surface
    temperature (D15, 2024 Shade Phoenix Plan) -- rank agreement."""
    lst = downscaling.lst_10m

    shade_plan = gpd.read_parquet(
        version_dir(d15_phoenix_open_data.SOURCE_ID, d15_phoenix_open_data.VERSION) / "shade_plan_tracts.parquet"
    )
    crs = f"EPSG:{load_neighborhood_config().target_epsg}"

    our_means: dict[str, float] = {}
    city_means: dict[str, float] = {}
    for _, row in shade_plan.iterrows():
        tract_id = str(row["GEOID_num"])
        our_mean = _zonal_mean(lst, row.geometry, crs)
        if not np.isfinite(our_mean):
            continue
        our_means[tract_id] = our_mean
        city_means[tract_id] = (float(row["avgLST_F_0"]) - 32.0) * 5.0 / 9.0  # F -> C

    common = sorted(our_means.keys() & city_means.keys())
    if len(common) < 3:
        return CityHotspotResult(spearman_rho=float("nan"), n_tracts=len(common), our_tract_means_c=our_means, city_tract_means_c=city_means)

    ours = pd.Series({k: our_means[k] for k in common})
    theirs = pd.Series({k: city_means[k] for k in common})
    rho = float(ours.corr(theirs, method="spearman"))
    return CityHotspotResult(
        spearman_rho=rho, n_tracts=len(common), our_tract_means_c=our_means, city_tract_means_c=city_means
    )


def run_validation() -> ValidationVerdict:
    from engine.thermal.downscale import run_downscaling

    downscaling = run_downscaling()  # computed once, shared -- each check used to re-run this independently
    station = check_station_correlation()
    landcover = check_landcover_contrast(downscaling)
    hotspot = check_city_hotspots(downscaling)

    reasons = []
    passed = True
    if not (np.isfinite(station.pearson_r) and station.pearson_r >= MIN_STATION_CORRELATION):
        passed = False
        reasons.append(
            f"station correlation r={station.pearson_r:.3f} < {MIN_STATION_CORRELATION} "
            f"(n={station.n_scenes} scenes)"
        )
    if not (np.isfinite(landcover.contrast_c) and landcover.contrast_c >= MIN_LANDCOVER_CONTRAST_C):
        passed = False
        reasons.append(
            f"parking-vs-park contrast {landcover.contrast_c:.2f}degC < {MIN_LANDCOVER_CONTRAST_C}degC "
            f"(parking n={landcover.n_parking_polygons}, park n={landcover.n_park_polygons})"
        )
    if not (np.isfinite(hotspot.spearman_rho) and hotspot.spearman_rho >= MIN_HOTSPOT_CORRELATION):
        passed = False
        reasons.append(
            f"city hot-spot rank correlation rho={hotspot.spearman_rho:.3f} < {MIN_HOTSPOT_CORRELATION} "
            f"(n={hotspot.n_tracts} tracts)"
        )

    return ValidationVerdict(station=station, landcover=landcover, hotspot=hotspot, passed=passed, reasons=reasons)
