"""D2 -- Sentinel-2 L2A (COOLBLOCK-BUILD-PLAN.md §5 data contract).

NDVI, NDBI, NDWI, albedo-proxy predictors for the TsHARP downscaling
regression (§6.1 A2). That regression needs one representative, largely
cloud-free 10m predictor surface per year to pair with each year's Landsat
composite -- not an exhaustive scene archive. A per-year, per-bbox search
on Planetary Computer returned 60-146 candidate scenes/year here (tile
overlap + reprocessing baselines cataloged separately, not true revisit
frequency), so this module picks the single lowest-cloud-cover scene per
summer rather than caching hundreds of largely redundant tiles.
"""

from __future__ import annotations

from pathlib import Path

import odc.stac
import planetary_computer
import pystac
import pystac_client
import xarray as xr

from engine.config import load_neighborhood_config
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "sentinel2_l2a"
VERSION = "2026-09-04"
LICENSE = "Copernicus Sentinel data, via Microsoft Planetary Computer"
PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "sentinel-2-l2a"
# B04 red, B08 NIR (NDVI), B11 SWIR (NDBI), B02 blue (albedo proxy), SCL (scene classification / cloud mask).
BANDS = ["B02", "B04", "B08", "B11", "SCL"]
NATIVE_RESOLUTION_M = 10
SUMMER_YEARS = [2021, 2022, 2023, 2024, 2025]
SUMMER_START_MD = "06-01"
SUMMER_END_MD = "09-30"
MAX_CLOUD_COVER_PCT = 20


def _best_item_per_year() -> list[pystac.Item]:
    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84.as_tuple()
    catalog = pystac_client.Client.open(PC_STAC_URL, modifier=planetary_computer.sign_inplace)

    best_items = []
    for year in SUMMER_YEARS:
        search = catalog.search(
            collections=[COLLECTION],
            bbox=bbox,
            datetime=f"{year}-{SUMMER_START_MD}/{year}-{SUMMER_END_MD}",
            query={"eo:cloud_cover": {"lt": MAX_CLOUD_COVER_PCT}},
        )
        items = list(search.items())
        if not items:
            continue
        best = min(items, key=lambda it: it.properties.get("eo:cloud_cover", 100))
        best_items.append(best)
    return best_items


def fetch_raw(items: list[pystac.Item]) -> xr.Dataset:
    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84.as_tuple()
    return odc.stac.load(
        items,
        bands=BANDS,
        bbox=bbox,
        crs=f"EPSG:{cfg.target_epsg}",
        resolution=NATIVE_RESOLUTION_M,
    )


def validate(ds: xr.Dataset, expected_years: int) -> None:
    assert ds.sizes["time"] > 0, "no Sentinel-2 scenes loaded"
    assert ds.sizes["time"] <= expected_years, "more scenes than one-per-year -- selection logic broke"
    red = ds["B04"].astype("float64")
    nir = ds["B08"].astype("float64")
    ndvi = (nir - red) / (nir + red).where((nir + red) != 0)
    valid_ndvi = ndvi.values[~ndvi.isnull().values]
    assert valid_ndvi.size > 0, "NDVI is entirely null"
    assert ((valid_ndvi >= -1) & (valid_ndvi <= 1)).mean() > 0.99, "NDVI outside its defined [-1,1] range"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    items = _best_item_per_year()
    ds = fetch_raw(items)
    validate(ds, expected_years=len(SUMMER_YEARS))

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "predictors_one_per_summer.nc"
    ds.to_netcdf(out_path, engine="h5netcdf")

    cfg = load_neighborhood_config()
    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=PC_STAC_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=cfg.bbox_wgs84.as_tuple(),
        extra={
            "scene_count": ds.sizes["time"],
            "bands": BANDS,
            "resolution_m": NATIVE_RESOLUTION_M,
            "selection": "min eo:cloud_cover, one scene per summer",
            "scene_ids": [it.id for it in items],
        },
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"sentinel2_l2a cached at {result_dir}")
