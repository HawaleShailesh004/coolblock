"""D4 -- OpenStreetMap / Overpass (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Buildings, roads, land use, existing trees, bus stops, schools, playgrounds.
Rate-limited, so cached immediately (§5's own risk note on D4) -- five
separate Overpass queries, one per layer, each written to its own GeoParquet
file under one manifest.
"""

from __future__ import annotations

import time
from pathlib import Path

import geopandas as gpd
import httpx
import osm2geojson
from shapely.geometry import shape

from engine.config import load_neighborhood_config
from engine.ingest.crs import to_canonical_crs_vector
from engine.ingest.grid import clip_to_canonical_grid
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "osm"
VERSION = "2026-09-04"
LICENSE = "ODbL 1.0 -- OpenStreetMap contributors"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT_S = 180
POLITE_DELAY_S = 10.0  # between sequential queries against the shared public instance
# overpass-api.de's Apache front end 406s requests with no descriptive User-Agent.
REQUEST_HEADERS = {
    "User-Agent": "CoolBlock/0.1 (NextStep Hacks 2026 -- github.com/coolblock; hackathon build)",
    "Accept": "*/*",
}

# Overpass bbox order is (south, west, north, east) == (min_lat, min_lon, max_lat, max_lon).
_QUERY_TEMPLATES: dict[str, str] = {
    "buildings": """
        [out:json][timeout:60];
        (
          way["building"]({bbox});
          relation["building"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    "roads": """
        [out:json][timeout:60];
        (
          way["highway"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    "landuse": """
        [out:json][timeout:60];
        (
          way["landuse"]({bbox});
          relation["landuse"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    "trees": """
        [out:json][timeout:60];
        (
          node["natural"="tree"]({bbox});
        );
        out body;
    """,
    "amenities": """
        [out:json][timeout:60];
        (
          node["amenity"="school"]({bbox});
          way["amenity"="school"]({bbox});
          node["leisure"="playground"]({bbox});
          way["leisure"="playground"]({bbox});
          node["highway"="bus_stop"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    # Added during Phase 4 (engine/surface/rule_layer.py): surface parking
    # lots read as plantable bare ground without this -- neither "roads"
    # (linear highway features) nor "buildings" (structures) captures them.
    "parking": """
        [out:json][timeout:60];
        (
          way["amenity"="parking"]({bbox});
          relation["amenity"="parking"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
}


def _bbox_str() -> str:
    cfg = load_neighborhood_config()
    b = cfg.bbox_wgs84
    return f"{b.min_lat},{b.min_lon},{b.max_lat},{b.max_lon}"


MAX_RETRIES = 8


def fetch_layer(layer: str) -> gpd.GeoDataFrame:
    query = _QUERY_TEMPLATES[layer].format(bbox=_bbox_str())

    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=REQUEST_TIMEOUT_S,
                headers=REQUEST_HEADERS,
            )
        except httpx.TransportError as exc:
            wait_s = 15.0 * (attempt + 1)
            print(f"  [{layer}] {exc!r}, retrying in {wait_s:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait_s)
            continue
        if resp.status_code not in (429, 502, 503, 504):
            break
        wait_s = float(resp.headers.get("Retry-After", 20 * (attempt + 1)))
        print(
            f"  [{layer}] HTTP {resp.status_code}, retrying in {wait_s:.0f}s "
            f"(attempt {attempt + 1}/{MAX_RETRIES})"
        )
        time.sleep(wait_s)
    assert resp is not None, f"all {MAX_RETRIES} attempts failed for layer {layer!r}"
    resp.raise_for_status()
    osm_json = resp.json()

    geojson = osm2geojson.json2geojson(osm_json)
    features = geojson.get("features", [])
    if not features:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")

    records = []
    for f in features:
        geom = shape(f["geometry"])
        tags = f.get("properties", {}).get("tags", {})
        records.append({**tags, "osm_type": f.get("properties", {}).get("type"), "geometry": geom})

    return gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")


def validate(layer: str, gdf: gpd.GeoDataFrame) -> None:
    # Trees and amenities can legitimately be sparse or absent in a given bbox;
    # buildings/roads/landuse should not be, or the bbox/query is wrong.
    if layer in ("buildings", "roads", "landuse"):
        assert len(gdf) > 0, f"OSM layer {layer!r} returned zero features -- check the query/bbox"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    cfg = load_neighborhood_config()
    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    counts: dict[str, int] = {}

    for i, layer in enumerate(_QUERY_TEMPLATES):
        out_path = vdir / f"{layer}.parquet"

        # Per-layer resumability: a prior run may have fetched this layer and
        # then failed on a later one (Overpass's shared instance is flaky).
        # Re-running shouldn't re-pay for layers already on disk.
        if not force and out_path.exists():
            print(f"  [{layer}] already on disk, skipping fetch")
            counts[layer] = len(gpd.read_parquet(out_path))
            files.append(out_path)
            continue

        gdf = fetch_layer(layer)
        validate(layer, gdf)
        if len(gdf) > 0:
            gdf = to_canonical_crs_vector(gdf)
            # Overpass returns the *complete* way/relation geometry for anything
            # that intersects the bbox, not a bbox-clipped fragment -- a long
            # arterial road or a large landuse zone can extend far past our
            # neighborhood. Clip to the canonical grid so cached data stays
            # scoped to the locked neighborhood (§1.3).
            gdf = clip_to_canonical_grid(gdf)
        else:
            gdf = gdf.set_crs(epsg=cfg.target_epsg, allow_override=True)

        gdf.to_parquet(out_path)
        files.append(out_path)
        counts[layer] = len(gdf)

        if i < len(_QUERY_TEMPLATES) - 1:
            time.sleep(POLITE_DELAY_S)

    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=OVERPASS_URL,
        license=LICENSE,
        files=files,
        bbox_wgs84=cfg.bbox_wgs84.as_tuple(),
        extra={"feature_counts": counts},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"osm cached at {result_dir}")
