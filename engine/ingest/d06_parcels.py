"""D6 -- Maricopa County Assessor parcels (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Parcel geometry, ownership class, land use code. Flagged Medium risk (R3,
city-specific) -- verified live against the locked bbox in Phase 1 hour 1,
before any other ingest module was written. See docs/adr/0003-*.md.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from engine.config import load_neighborhood_config
from engine.ingest.arcgis import query_layer_by_bbox
from engine.ingest.crs import to_canonical_crs_vector
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "maricopa_parcels"
VERSION = "2026-09-04"
LICENSE = "Public domain -- Maricopa County Assessor's Office open data"
SERVICE_URL = "https://gis.mcassessor.maricopa.gov/arcgis/rest/services/Parcels/MapServer/0/query"
OUT_FIELDS = [
    "APN",
    "OWNER_NAME",
    "PHYSICAL_ADDRESS",
    "PHYSICAL_CITY",
    "PHYSICAL_ZIP",
    "LC_CUR",
    "JURISDICTION",
    "LAND_SIZE",
    "CONST_YEAR",
    "SUBNAME",
]
def fetch_raw() -> gpd.GeoDataFrame:
    cfg = load_neighborhood_config()
    gdf = query_layer_by_bbox(SERVICE_URL, cfg.bbox_wgs84, out_fields=OUT_FIELDS)
    if len(gdf) == 0:
        raise RuntimeError("Maricopa parcels query returned zero features for the locked bbox")
    return gdf


def validate(gdf: gpd.GeoDataFrame) -> None:
    assert len(gdf) > 0, "no parcels returned"
    assert gdf.geometry.is_valid.mean() > 0.99, "too many invalid parcel geometries"
    assert gdf["APN"].notna().mean() > 0.99, "too many parcels missing APN"

    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84
    minx, miny, maxx, maxy = gdf.total_bounds
    pad = 0.01  # deg -- parcels straddling the bbox edge legitimately poke outside it
    assert minx >= bbox.min_lon - pad and maxx <= bbox.max_lon + pad, "parcels fall outside locked bbox (lon)"
    assert miny >= bbox.min_lat - pad and maxy <= bbox.max_lat + pad, "parcels fall outside locked bbox (lat)"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    gdf = fetch_raw()
    validate(gdf)
    projected = to_canonical_crs_vector(gdf)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "parcels.parquet"
    projected.to_parquet(out_path)

    cfg = load_neighborhood_config()
    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=SERVICE_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=cfg.bbox_wgs84.as_tuple(),
        extra={"feature_count": len(projected), "fields": OUT_FIELDS},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"maricopa_parcels cached at {result_dir}")
