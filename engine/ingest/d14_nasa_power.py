"""D14 -- NASA POWER (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Daily solar irradiance for the shade/albedo energy-balance model (§6.3 C3).
Keyless REST, point data at the neighborhood centroid, same 2021-2025 summer
window as D13 so the two series line up.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pandas as pd

from engine.config import load_neighborhood_config
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "nasa_power"
VERSION = "2026-09-04"
LICENSE = "Public domain -- NASA POWER Project"
BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
REQUEST_TIMEOUT_S = 60

SUMMER_YEARS = [2021, 2022, 2023, 2024, 2025]
SUMMER_START_MD = "0601"
SUMMER_END_MD = "0930"
# ALLSKY_SFC_SW_DWN: all-sky surface shortwave downward irradiance (kW-hr/m^2/day)
# T2M: air temperature at 2m, as a cross-check against Open-Meteo (D13)
PARAMETERS = ["ALLSKY_SFC_SW_DWN", "T2M", "T2M_MAX", "T2M_MIN"]


def _centroid() -> tuple[float, float]:
    cfg = load_neighborhood_config()
    b = cfg.bbox_wgs84
    return (b.min_lat + b.max_lat) / 2, (b.min_lon + b.max_lon) / 2


def fetch_raw() -> pd.DataFrame:
    lat, lon = _centroid()
    frames = []

    for year in SUMMER_YEARS:
        resp = httpx.get(
            BASE_URL,
            params={
                "parameters": ",".join(PARAMETERS),
                "community": "RE",
                "longitude": lon,
                "latitude": lat,
                "start": f"{year}{SUMMER_START_MD}",
                "end": f"{year}{SUMMER_END_MD}",
                "format": "JSON",
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        payload = resp.json()
        if "messages" in payload and payload.get("messages"):
            raise RuntimeError(f"NASA POWER query failed for {year}: {payload['messages']}")

        params = payload["properties"]["parameter"]
        dates = sorted(params[PARAMETERS[0]].keys())
        rows = [{"date": d, **{p: params[p][d] for p in PARAMETERS}} for d in dates]
        frames.append(pd.DataFrame(rows))

    return pd.concat(frames, ignore_index=True)


# NASA POWER's documented fill value for a missing observation.
FILL_VALUE = -999.0


def validate(df: pd.DataFrame) -> None:
    assert len(df) > 0, "no NASA POWER rows returned"
    irradiance = df["ALLSKY_SFC_SW_DWN"].replace(FILL_VALUE, pd.NA)
    irradiance = pd.to_numeric(irradiance, errors="coerce")
    # kW-hr/m^2/day -- a plausibility band for the Sonoran Desert in summer.
    assert irradiance.between(3, 12).mean() > 0.9, "ALLSKY_SFC_SW_DWN outside a plausible range"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    df = fetch_raw()
    validate(df)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "daily_summer_2021_2025.parquet"
    df.to_parquet(out_path)

    lat, lon = _centroid()
    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=BASE_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=None,
        extra={
            "row_count": len(df),
            "point": {"lat": lat, "lon": lon},
            "years": SUMMER_YEARS,
            "parameters": PARAMETERS,
            "fill_value": FILL_VALUE,
        },
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"nasa_power cached at {result_dir}")
