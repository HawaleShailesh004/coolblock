"""D10 -- Tree Equity Score (COOLBLOCK-BUILD-PLAN.md §5 data contract).

American Forests does not publish a documented public API for Tree Equity
Score (verified during Phase 1 research -- treeequityscore.org exposes only
an interactive map, no REST endpoint). This module uses a public ArcGIS
mirror of the published Phoenix, AZ 2020 block-group scores (item
74fb41a4c31e4709858be6d7dcb4382f, owned by a Charles University researcher)
that carries the standard TES methodology fields (tes, tc_gap, pctpoc,
pctpov, temp) -- not the official API, and labeled as such everywhere it's
used, per the honesty rail (§1.4).
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from engine.config import load_neighborhood_config
from engine.ingest.arcgis import query_layer_by_bbox
from engine.ingest.crs import to_canonical_crs_vector
from engine.ingest.grid import clip_to_canonical_grid
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "tree_equity_score"
VERSION = "2026-09-04"
LICENSE = (
    "Derived from American Forests Tree Equity Score methodology; this mirror is a "
    "third-party public republication (ArcGIS item 74fb41a4c31e4709858be6d7dcb4382f), "
    "not the official American Forests API -- see module docstring."
)
SERVICE_URL = (
    "https://services1.arcgis.com/LPm07959azIAvFRD/arcgis/rest/services/"
    "Tree_Equity_Score_2020/FeatureServer/11/query"
)
OUT_FIELDS = [
    "GEOID",
    "city_name",
    "total_pop",
    "tes",  # Tree Equity Score, 0-100, higher is better
    "tc_gap",  # tree canopy gap vs. goal
    "tc_goal",
    "nlcdcanopy",
    "pctpoc",
    "pctpov",
    "temp",
    "equity_ind",
]


def fetch_raw() -> gpd.GeoDataFrame:
    cfg = load_neighborhood_config()
    gdf = query_layer_by_bbox(SERVICE_URL, cfg.bbox_wgs84, out_fields=OUT_FIELDS)
    if len(gdf) == 0:
        raise RuntimeError("Tree Equity Score query returned zero block groups for the locked bbox")
    return gdf


def validate(gdf: gpd.GeoDataFrame) -> None:
    assert len(gdf) > 0, "no Tree Equity Score block groups returned"
    assert gdf["GEOID"].notna().mean() > 0.99, "too many block groups missing GEOID"
    assert gdf["tes"].between(0, 100).mean() > 0.95, "tes outside the documented [0,100] range"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    gdf = fetch_raw()
    validate(gdf)
    projected = clip_to_canonical_grid(to_canonical_crs_vector(gdf))

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "tes_block_groups.parquet"
    projected.to_parquet(out_path)

    cfg = load_neighborhood_config()
    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=SERVICE_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=cfg.bbox_wgs84.as_tuple(),
        extra={"feature_count": len(projected), "fields": OUT_FIELDS, "score_vintage": "2020"},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"tree_equity_score cached at {result_dir}")
