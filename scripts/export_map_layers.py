"""Exports cached Phase 1 vector layers to GeoJSON for the map app (Phase 2).

Phase 2 scope is "get pixels on screen," not the real API/DB serving layer
(that's Phase 7 -- FastAPI + PostGIS + PMTiles generation). This is a
one-off static export: data/cache/*.parquet (engine.ingest's output) ->
data/derived/edison-eastlake/*.geojson (apps/web reads these directly).
Re-run whenever the underlying ingest cache changes.

Building heights are estimated, not measured -- most OSM buildings here
carry no height/building:levels tag (94 of 2,844 have building:levels; 1
has an explicit height). Estimated heights are real numbers derived from a
documented, disclosed heuristic, not invented ones; the frontend labels
them as estimated. See _estimate_height_m below for the exact rule.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from engine.ingest import d04_osm, d06_parcels
from engine.ingest.manifest import version_dir

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "derived" / "edison-eastlake"

METRES_PER_LEVEL = 3.5
ROOF_ALLOWANCE_M = 1.0
# Fallback height by OSM `building` tag value, for the ~97% of buildings
# with no height/levels tag at all. Rough, disclosed, and labeled as
# estimated wherever it's rendered -- not presented as measured.
DEFAULT_HEIGHT_BY_TYPE = {
    "house": 5.0,
    "residential": 5.0,
    "detached": 5.0,
    "terrace": 6.0,
    "apartments": 12.0,
    "commercial": 8.0,
    "retail": 7.0,
    "industrial": 8.0,
    "university": 10.0,
    "school": 8.0,
    "church": 12.0,
    "garage": 3.0,
    "carport": 3.0,
    "shed": 3.0,
    "roof": 3.0,
    "service": 4.0,
}
DEFAULT_HEIGHT_M = 5.0


def _parse_height_tag(value: object) -> float | None:
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return None
    s = str(value).strip().lower().replace("m", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _estimate_height_m(row: gpd.GeoSeries) -> tuple[float, str]:
    """Returns (height_m, provenance) -- provenance is surfaced to the UI,
    never silently blended with measured values."""
    height = _parse_height_tag(row.get("height"))
    if height is not None and height > 0:
        return height, "measured"

    levels = _parse_height_tag(row.get("building:levels"))
    if levels is not None and levels > 0:
        return levels * METRES_PER_LEVEL + ROOF_ALLOWANCE_M, "levels"

    building_type = str(row.get("building") or "").lower()
    return DEFAULT_HEIGHT_BY_TYPE.get(building_type, DEFAULT_HEIGHT_M), "estimated_default"


def export_buildings() -> Path:
    gdf = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "buildings.parquet")
    gdf = gdf.to_crs(epsg=4326)  # GeoJSON is WGS84 by convention; MapLibre expects it

    heights, provenances = zip(*(_estimate_height_m(row) for _, row in gdf.iterrows()), strict=True)
    out = gpd.GeoDataFrame(
        {
            "name": gdf.get("name"),
            "building_type": gdf.get("building"),
            "height_m": heights,
            "height_provenance": provenances,
            "geometry": gdf.geometry,
        },
        crs="EPSG:4326",
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "buildings.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_roads() -> Path:
    gdf = gpd.read_parquet(version_dir(d04_osm.SOURCE_ID, d04_osm.VERSION) / "roads.parquet")
    gdf = gdf.to_crs(epsg=4326)
    out = gpd.GeoDataFrame(
        {"name": gdf.get("name"), "highway": gdf.get("highway"), "geometry": gdf.geometry},
        crs="EPSG:4326",
    )
    out_path = OUT_DIR / "roads.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def export_parcels() -> Path:
    gdf = gpd.read_parquet(version_dir(d06_parcels.SOURCE_ID, d06_parcels.VERSION) / "parcels.parquet")
    gdf = gdf.to_crs(epsg=4326)
    out = gpd.GeoDataFrame(
        {"apn": gdf.get("APN"), "land_use_code": gdf.get("LC_CUR"), "geometry": gdf.geometry},
        crs="EPSG:4326",
    )
    out_path = OUT_DIR / "parcels.geojson"
    out.to_file(out_path, driver="GeoJSON")
    return out_path


def main() -> None:
    for label, fn in [("buildings", export_buildings), ("roads", export_roads), ("parcels", export_parcels)]:
        path = fn()
        size_kb = path.stat().st_size / 1024
        print(f"{label}: {path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
