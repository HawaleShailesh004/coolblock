"""Loads config/neighborhood.toml -- the scope lock (COOLBLOCK-BUILD-PLAN.md §1.3, §3.1).

Every engine module that needs the target bbox, CRS, or grid resolution reads
it from here rather than hardcoding it a second time.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NEIGHBORHOOD_CONFIG_PATH = REPO_ROOT / "config" / "neighborhood.toml"


@dataclass(frozen=True)
class BBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)


@dataclass(frozen=True)
class NeighborhoodConfig:
    id: str
    name: str
    city: str
    state: str
    country: str
    bbox_wgs84: BBox
    target_epsg: int
    wgs84_epsg: int
    grid_resolution_m: int
    timezone_iana: str


@lru_cache(maxsize=1)
def load_neighborhood_config(path: Path = NEIGHBORHOOD_CONFIG_PATH) -> NeighborhoodConfig:
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    n = raw["neighborhood"]
    bbox = n["bbox_wgs84"]
    crs = n["crs"]
    tz = n["timezone"]

    return NeighborhoodConfig(
        id=n["id"],
        name=n["name"],
        city=n["city"],
        state=n["state"],
        country=n["country"],
        bbox_wgs84=BBox(
            min_lon=bbox["min_lon"],
            min_lat=bbox["min_lat"],
            max_lon=bbox["max_lon"],
            max_lat=bbox["max_lat"],
        ),
        target_epsg=crs["target_epsg"],
        wgs84_epsg=crs["wgs84_epsg"],
        grid_resolution_m=crs["grid_resolution_m"],
        timezone_iana=tz["iana"],
    )
