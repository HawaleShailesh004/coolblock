"""D1 -- Landsat 8/9 Collection 2 L2 (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Surface temperature (`lwir11`, Collection 2's renamed `ST_B10`) and the QA
mask, June-Sept across 2021-2025 -- the exact scenes engine.thermal's
composite (§6.1 A1) will later cloud-mask and median-reduce. This module
only fetches, validates, and caches the raw scenes; the composite itself is
Phase 3 work.

Cached as a single NetCDF, not one COG per date -- a (time, y, x) cube is
the natural shape for "every scene over 5 summers" and is what Phase 3
will load directly via rioxarray/xarray. Reprojected onto the same CRS and
grid origin as the canonical 10m grid, but at Landsat's native 30m
resolution (30 = 3x10, so pixel edges still land on the 10m grid lines) --
the 30m->10m step is TsHARP downscaling (Phase 3 science), not an ingest
resample.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import odc.stac
import planetary_computer
import pystac
import pystac_client
import xarray as xr

from engine.config import load_neighborhood_config
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "landsat_c2_l2"
VERSION = "2026-09-04"
LICENSE = "Public domain -- USGS/NASA Landsat, via Microsoft Planetary Computer"
PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "landsat-c2-l2"
BANDS = ["lwir11", "qa_pixel"]
NATIVE_RESOLUTION_M = 30
SUMMER_YEARS = [2021, 2022, 2023, 2024, 2025]
SUMMER_START_MD = "06-01"
SUMMER_END_MD = "09-30"
PLATFORMS = ["landsat-8", "landsat-9"]

# Collection 2 L2 thermal DN -> Kelvin (COOLBLOCK-BUILD-PLAN.md §6.1 A1).
ST_SCALE = 0.00341802
ST_OFFSET = 149.0


def search_items() -> list[pystac.Item]:
    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84.as_tuple()
    catalog = pystac_client.Client.open(PC_STAC_URL, modifier=planetary_computer.sign_inplace)

    items: list[pystac.Item] = []
    for year in SUMMER_YEARS:
        search = catalog.search(
            collections=[COLLECTION],
            bbox=bbox,
            datetime=f"{year}-{SUMMER_START_MD}/{year}-{SUMMER_END_MD}",
            query={"platform": {"in": PLATFORMS}},
        )
        items.extend(search.items())
    return items


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


def validate(ds: xr.Dataset) -> None:
    assert ds.sizes["time"] > 0, "no Landsat scenes loaded"
    st_kelvin = ds["lwir11"].astype("float64") * ST_SCALE + ST_OFFSET
    valid = st_kelvin.values[~np.isnan(st_kelvin.values) & (ds["lwir11"].values > 0)]
    assert valid.size > 0, "no valid (non-fill) thermal pixels in any scene"
    st_celsius = valid - 273.15
    # Phoenix summer surface temperature -- a plausibility band, not a model.
    assert ((st_celsius > 10) & (st_celsius < 90)).mean() > 0.5, (
        "converted surface temperatures outside a plausible range"
    )


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    items = search_items()
    ds = fetch_raw(items)
    validate(ds)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "lwir11_qa_2021_2025.nc"
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
            "years": SUMMER_YEARS,
            "st_scale": ST_SCALE,
            "st_offset": ST_OFFSET,
        },
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"landsat_c2_l2 cached at {result_dir}")
