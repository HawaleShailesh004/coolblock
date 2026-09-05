"""D7b -- Census TIGER/Line block group boundaries (added Phase 5).

Not one of the original 16 data-contract sources -- added when Phase 5's
dasymetric population redistribution (engine/equity/population.py) needed
real block-group *polygons* to spatially join buildings against, and the
only other block-group polygon set already cached (D10, Tree Equity
Score, 2020 vintage) only matched 9 of D7's 23 block groups (Census
periodically redraws block-group boundaries; TES and ACS 2022 don't
share a vintage). Keyless REST, direct from Census.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import httpx

from engine.config import load_neighborhood_config
from engine.ingest.crs import to_canonical_crs_vector
from engine.ingest.grid import clip_to_canonical_grid
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "tiger_block_groups"
VERSION = "2026-09-04"
LICENSE = "Public domain -- US Census Bureau, TIGER/Line 2022"
TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_04_bg.zip"
STATE_FIPS = "04"
COUNTY_FIPS = "013"
REQUEST_TIMEOUT_S = 120


def fetch_raw() -> gpd.GeoDataFrame:
    resp = httpx.get(TIGER_URL, timeout=REQUEST_TIMEOUT_S, follow_redirects=True)
    resp.raise_for_status()

    import io
    import zipfile

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        shp_name = next(n for n in zf.namelist() if n.endswith(".shp"))
        # geopandas needs all the shapefile sidecar files on disk together.
        tmp_dir = version_dir(SOURCE_ID, VERSION) / "_raw"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        zf.extractall(tmp_dir)
        gdf = gpd.read_file(tmp_dir / shp_name)

    gdf = gdf[(gdf["STATEFP"] == STATE_FIPS) & (gdf["COUNTYFP"] == COUNTY_FIPS)]

    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    clipped = gdf_wgs84.cx[bbox.min_lon : bbox.max_lon, bbox.min_lat : bbox.max_lat]
    return clipped


def validate(gdf: gpd.GeoDataFrame) -> None:
    assert len(gdf) > 0, "no block group boundaries returned for the locked bbox"
    assert gdf["GEOID"].notna().all(), "block groups missing GEOID"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    gdf = fetch_raw()
    validate(gdf)
    projected = clip_to_canonical_grid(to_canonical_crs_vector(gdf))

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "block_groups.parquet"
    projected[["GEOID", "ALAND", "geometry"]].to_parquet(out_path)

    # The raw shapefile sidecar files aren't needed once vectorized.
    import shutil

    shutil.rmtree(vdir / "_raw", ignore_errors=True)

    cfg = load_neighborhood_config()
    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=TIGER_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=cfg.bbox_wgs84.as_tuple(),
        extra={"feature_count": len(projected), "vintage": "TIGER2022"},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"tiger_block_groups cached at {result_dir}")
