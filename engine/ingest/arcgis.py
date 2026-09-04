"""Shared ArcGIS REST FeatureServer/MapServer query helper.

D6, D8, D10, and D15 all query an ArcGIS layer by bbox and page through
`exceededTransferLimit`. Factored out once it showed up the third time --
not a speculative abstraction.
"""

from __future__ import annotations

import geopandas as gpd
import httpx

from engine.config import BBox

PAGE_SIZE = 1000
REQUEST_TIMEOUT_S = 30


def query_layer_by_bbox(
    layer_query_url: str,
    bbox: BBox,
    *,
    out_fields: list[str] | str = "*",
    where: str = "1=1",
    page_size: int = PAGE_SIZE,
) -> gpd.GeoDataFrame:
    """GET-query an ArcGIS Feature/MapServer layer's /query endpoint, paginated."""
    fields = out_fields if isinstance(out_fields, str) else ",".join(out_fields)
    features: list[dict[str, object]] = []
    offset = 0

    while True:
        resp = httpx.get(
            layer_query_url,
            params={
                "where": where,
                "geometry": f"{bbox.min_lon},{bbox.min_lat},{bbox.max_lon},{bbox.max_lat}",
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": fields,
                "returnGeometry": "true",
                "resultRecordCount": page_size,
                "resultOffset": offset,
                "f": "geojson",
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        payload = resp.json()
        if "error" in payload:
            raise RuntimeError(f"ArcGIS query failed ({layer_query_url}): {payload['error']}")

        batch = payload.get("features", [])
        features.extend(batch)
        exceeded = payload.get("properties", {}).get("exceededTransferLimit", False)
        if not batch or (not exceeded and len(batch) < page_size):
            break
        offset += page_size

    if not features:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
