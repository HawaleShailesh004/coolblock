"""D8 -- CDC/ATSDR Social Vulnerability Index (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Composite social vulnerability, tract level, 2022 release. Feeds directly
into the Heat Vulnerability Index (engine.equity, Phase 5, §6.4 D2).
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from engine.config import load_neighborhood_config
from engine.ingest.arcgis import query_layer_by_bbox
from engine.ingest.crs import to_canonical_crs_vector
from engine.ingest.grid import clip_to_canonical_grid
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "cdc_svi"
VERSION = "2026-09-04"
LICENSE = "Public domain -- CDC/ATSDR"
# Layer 2 = "SVI2022 US tract" on the CDC/ATSDR SVI 2022 USA service (onemap.cdc.gov).
SERVICE_URL = (
    "https://onemap.cdc.gov/onemapservices/rest/services/SVI/"
    "CDC_ATSDR_Social_Vulnerability_Index_2022_USA/MapServer/2/query"
)
OUT_FIELDS = [
    "FIPS",
    "LOCATION",
    "E_TOTPOP",
    "RPL_THEME1",  # Socioeconomic Status
    "RPL_THEME2",  # Household Characteristics
    "RPL_THEME3",  # Racial & Ethnic Minority Status
    "RPL_THEME4",  # Housing Type & Transportation
    "RPL_THEMES",  # Overall composite SVI percentile rank
]


def fetch_raw() -> gpd.GeoDataFrame:
    cfg = load_neighborhood_config()
    gdf = query_layer_by_bbox(SERVICE_URL, cfg.bbox_wgs84, out_fields=OUT_FIELDS)
    if len(gdf) == 0:
        raise RuntimeError("CDC SVI query returned zero tracts for the locked bbox")
    return gdf


def validate(gdf: gpd.GeoDataFrame) -> None:
    assert len(gdf) > 0, "no SVI tracts returned"
    assert gdf["FIPS"].notna().mean() > 0.99, "too many tracts missing FIPS"
    # RPL_THEMES is a percentile rank in [0, 1]; -999 is CDC's documented missing-data sentinel.
    valid = gdf.loc[gdf["RPL_THEMES"] != -999, "RPL_THEMES"]
    assert valid.between(0, 1).mean() > 0.95, "RPL_THEMES out of the documented [0,1] range"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    gdf = fetch_raw()
    validate(gdf)
    projected = clip_to_canonical_grid(to_canonical_crs_vector(gdf))

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "svi_tracts.parquet"
    projected.to_parquet(out_path)

    cfg = load_neighborhood_config()
    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=SERVICE_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=cfg.bbox_wgs84.as_tuple(),
        extra={"feature_count": len(projected), "fields": OUT_FIELDS, "svi_release": "2022"},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"cdc_svi cached at {result_dir}")
