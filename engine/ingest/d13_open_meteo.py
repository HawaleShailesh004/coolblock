"""D13 -- Open-Meteo (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Historical hourly air temperature for thermal-surface validation (§6.1 A3)
and design-day conditions for the shade raytrace (§6.3 C2). Keyless REST,
point data at the neighborhood centroid.

Summer window (June-Sept) across the same 2021-2025 span the thermal
composite pulls Landsat scenes from (§6.1 A1) -- the validation only means
something if both series cover the same years.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pandas as pd

from engine.config import load_neighborhood_config
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "open_meteo"
VERSION = "2026-09-04"
LICENSE = "CC BY 4.0 -- Open-Meteo (source: reanalysis, national weather services)"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
REQUEST_TIMEOUT_S = 60

SUMMER_YEARS = [2021, 2022, 2023, 2024, 2025]
SUMMER_START_MD = "06-01"
SUMMER_END_MD = "09-30"
HOURLY_VARS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m"]


def _centroid() -> tuple[float, float]:
    cfg = load_neighborhood_config()
    b = cfg.bbox_wgs84
    return (b.min_lat + b.max_lat) / 2, (b.min_lon + b.max_lon) / 2


def fetch_raw() -> pd.DataFrame:
    lat, lon = _centroid()
    cfg = load_neighborhood_config()
    frames = []

    for year in SUMMER_YEARS:
        resp = httpx.get(
            ARCHIVE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": f"{year}-{SUMMER_START_MD}",
                "end_date": f"{year}-{SUMMER_END_MD}",
                "hourly": ",".join(HOURLY_VARS),
                "timezone": cfg.timezone_iana,
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        payload = resp.json()
        if "error" in payload:
            raise RuntimeError(f"Open-Meteo query failed for {year}: {payload.get('reason')}")
        frames.append(pd.DataFrame(payload["hourly"]))

    return pd.concat(frames, ignore_index=True)


def validate(df: pd.DataFrame) -> None:
    assert len(df) > 0, "no Open-Meteo rows returned"
    assert df["time"].notna().mean() > 0.99, "too many rows missing timestamp"
    temp = pd.to_numeric(df["temperature_2m"], errors="coerce")
    # Phoenix summer air temperature, deg C -- a plausibility band, not a model.
    assert temp.between(15, 55).mean() > 0.95, "temperature_2m outside a plausible Phoenix summer range"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    df = fetch_raw()
    validate(df)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "hourly_summer_2021_2025.parquet"
    df.to_parquet(out_path)

    lat, lon = _centroid()
    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=ARCHIVE_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=None,
        extra={
            "row_count": len(df),
            "point": {"lat": lat, "lon": lon},
            "years": SUMMER_YEARS,
            "variables": HOURLY_VARS,
        },
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"open_meteo cached at {result_dir}")
