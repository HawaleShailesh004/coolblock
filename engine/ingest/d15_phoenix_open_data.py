"""D15 -- Phoenix Open Data (COOLBLOCK-BUILD-PLAN.md §5 data contract).

The city's own 2024 Shade Phoenix Plan tract-level dataset: average land
surface temperature, tree canopy %, shade coverage at 12pm/3pm/6pm, sidewalk
shade, income group, and federal Justice40 (CEJST) / Qualified Census Tract
flags -- published by the City of Phoenix's official GIS account.

This is richer than a plain street-tree inventory (the data contract's
original description), and it directly serves §6.1 A3's third validation
check: "confirm the surface reproduces hot spots the city already names in
its published plans" -- avgLST_F is exactly that, from the city's own plan.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from engine.config import load_neighborhood_config
from engine.ingest.arcgis import query_layer_by_bbox
from engine.ingest.crs import to_canonical_crs_vector
from engine.ingest.grid import clip_to_canonical_grid
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "phoenix_shade_plan"
VERSION = "2026-09-04"
LICENSE = "Public domain -- City of Phoenix Office of Heat Response and Mitigation"
SERVICE_URL = (
    "https://services.arcgis.com/cfKakmeHE95cgeEK/arcgis/rest/services/"
    "2024ShadePlanData/FeatureServer/0/query"
)
OUT_FIELDS = [
    "GEOID_num",
    "NAME",
    "village",
    "DISTRICT",
    "TOTAL_POPU",
    "avgLST_F_0",  # average land surface temperature, deg F -- the city's own hot-spot data
    "tree_pct",
    "shade12pm_",
    "shade3pm_p",
    "shade6pm_p",
    "pct_sidewa",
    "inCEJST",  # federal Justice40 Climate and Economic Justice Screening Tool flag
    "inQCT",  # Qualified Census Tract
    "income_gro",
]


def fetch_raw() -> gpd.GeoDataFrame:
    cfg = load_neighborhood_config()
    gdf = query_layer_by_bbox(SERVICE_URL, cfg.bbox_wgs84, out_fields=OUT_FIELDS)
    if len(gdf) == 0:
        raise RuntimeError("Phoenix Shade Plan query returned zero tracts for the locked bbox")
    return gdf


def validate(gdf: gpd.GeoDataFrame) -> None:
    assert len(gdf) > 0, "no Shade Plan tracts returned"
    assert gdf["GEOID_num"].notna().mean() > 0.99, "too many tracts missing GEOID"
    # Phoenix summer LST readings run well above air temperature; a plausibility band, not a model.
    assert gdf["avgLST_F_0"].between(80, 180).mean() > 0.9, "avgLST_F_0 outside a plausible range"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    gdf = fetch_raw()
    validate(gdf)
    projected = clip_to_canonical_grid(to_canonical_crs_vector(gdf))

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "shade_plan_tracts.parquet"
    projected.to_parquet(out_path)

    cfg = load_neighborhood_config()
    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=SERVICE_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=cfg.bbox_wgs84.as_tuple(),
        extra={"feature_count": len(projected), "fields": OUT_FIELDS, "plan_vintage": "2024"},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"phoenix_shade_plan cached at {result_dir}")
