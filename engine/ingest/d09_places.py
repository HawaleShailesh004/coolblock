"""D9 -- CDC PLACES (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Asthma, COPD, CHD, diabetes prevalence, tract level. PLACES has no polygon
geometry of its own (a point "geolocation" per tract, no boundary) -- so
this module keys off the exact tract FIPS codes D8 (CDC SVI) already
resolved for our bbox, rather than re-deriving which tracts are "ours" a
second, possibly inconsistent way. Run D8 first.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import httpx
import pandas as pd

from engine.ingest import d08_svi
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "cdc_places"
VERSION = "2026-09-04"
LICENSE = "Public domain -- CDC PLACES, 2025 release (GIS-friendly, census tract)"
SOCRATA_URL = "https://data.cdc.gov/resource/yjkw-uj5s.json"
REQUEST_TIMEOUT_S = 30

FIELDS = [
    "tractfips",
    "totalpopulation",
    "casthma_crudeprev",  # current asthma
    "copd_crudeprev",
    "chd_crudeprev",  # coronary heart disease
    "diabetes_crudeprev",
]


def _target_tract_fips() -> list[str]:
    """The tract FIPS codes D8 already resolved for the locked bbox."""
    svi_dir = version_dir(d08_svi.SOURCE_ID, d08_svi.VERSION)
    gdf = gpd.read_parquet(svi_dir / "svi_tracts.parquet")
    return sorted(gdf["FIPS"].dropna().unique().tolist())


def fetch_raw(tract_fips: list[str]) -> pd.DataFrame:
    fips_list = ",".join(f"'{f}'" for f in tract_fips)
    resp = httpx.get(
        SOCRATA_URL,
        params={
            "$select": ",".join(FIELDS),
            "$where": f"tractfips in ({fips_list})",
            "$limit": 5000,
        },
        timeout=REQUEST_TIMEOUT_S,
    )
    resp.raise_for_status()
    rows = resp.json()
    if isinstance(rows, dict) and "message" in rows:
        raise RuntimeError(f"CDC PLACES query failed: {rows['message']}")
    return pd.DataFrame(rows)


def validate(df: pd.DataFrame, expected_fips: list[str]) -> None:
    assert len(df) > 0, "no PLACES rows returned"
    got = set(df["tractfips"])
    missing = set(expected_fips) - got
    assert len(missing) <= 1, f"PLACES missing data for tracts: {missing}"
    for col in ("casthma_crudeprev", "chd_crudeprev"):
        rate = pd.to_numeric(df[col], errors="coerce")
        assert rate.between(0, 100).mean() > 0.95, f"{col} outside plausible [0,100] range"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    tract_fips = _target_tract_fips()
    df = fetch_raw(tract_fips)
    validate(df, tract_fips)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "places_tracts.parquet"
    df.to_parquet(out_path)

    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=SOCRATA_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=None,  # tabular, keyed by tract FIPS -- see D8 for the spatial join
        extra={"row_count": len(df), "fields": FIELDS, "tract_fips": tract_fips},
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"cdc_places cached at {result_dir}")
