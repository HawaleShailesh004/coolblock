"""D7 -- Census ACS 5-year (COOLBLOCK-BUILD-PLAN.md §5 data contract).

Median income, poverty rate, age <5 and 65+, tenure, vehicle access,
population. Keys off the exact tract FIPS codes D8 (CDC SVI) already
resolved for the locked bbox -- run D8 first.

Two geographies, not one, and this is a real ACS constraint, not a bug:
population/income/age/tenure (B01003, B19013, B01001, B25003) are published
at block-group level, but poverty status (B17001) and vehicle availability
(B08201) are only published at tract level -- verified live during Phase 1
(both return null for every block group, non-null at tract). Tract-level
values are broadcast to their constituent block groups, flagged via
`*_is_tract_level` columns rather than silently presented as block-group
precision they don't have.

Requires CENSUS_API_KEY in the environment (free, instant signup at
https://api.census.gov/data/key_signup.html) -- see .env.example.
"""

from __future__ import annotations

import os
from pathlib import Path

import geopandas as gpd
import httpx
import pandas as pd
from dotenv import load_dotenv

from engine.ingest import d08_svi
from engine.ingest.manifest import is_cached, version_dir, write_manifest

SOURCE_ID = "census_acs5"
VERSION = "2026-09-04"
LICENSE = "Public domain -- US Census Bureau, ACS 5-year 2022"
ACS_YEAR = 2022
BASE_URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
REQUEST_TIMEOUT_S = 30
STATE_FIPS = "04"
COUNTY_FIPS = "013"

# Verified live against api.census.gov/data/2022/acs/acs5/variables/<code>.json
# and against real block-group/tract queries during Phase 1 -- not assumed.
_MALE_65_PLUS = [f"B01001_0{n}E" for n in range(20, 26)]  # 020..025
_FEMALE_65_PLUS = [f"B01001_0{n}E" for n in range(44, 50)]  # 044..049

BLOCK_GROUP_VARIABLES = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B25003_001E": "occupied_housing_units",
    "B25003_002E": "owner_occupied",
    "B25003_003E": "renter_occupied",
    "B01001_003E": "male_under5",
    "B01001_027E": "female_under5",
    **{v: f"male_65_{v[-3:-1]}" for v in _MALE_65_PLUS},
    **{v: f"female_65_{v[-3:-1]}" for v in _FEMALE_65_PLUS},
}

# Not published at block-group level (verified live, §module docstring) -- tract only.
TRACT_ONLY_VARIABLES = {
    "B17001_001E": "poverty_universe",
    "B17001_002E": "poverty_count",
    "B08201_001E": "households_total",
    "B08201_002E": "households_no_vehicle",
}


def _target_tracts() -> list[str]:
    """6-digit tract codes, derived from the FIPS D8 already resolved for the bbox."""
    svi_dir = version_dir(d08_svi.SOURCE_ID, d08_svi.VERSION)
    gdf = gpd.read_parquet(svi_dir / "svi_tracts.parquet")
    fips = sorted(gdf["FIPS"].dropna().unique().tolist())
    return [f[5:] for f in fips]  # state(2) + county(3) + tract(6) -> tract only


def _api_key() -> str:
    load_dotenv()
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise RuntimeError(
            "CENSUS_API_KEY not set. Get a free, instant key at "
            "https://api.census.gov/data/key_signup.html and add it to .env."
        )
    return key


def _fetch_block_groups(key: str, tracts: list[str]) -> pd.DataFrame:
    frames = []
    for tract in tracts:
        resp = httpx.get(
            BASE_URL,
            params={
                "get": ",".join(BLOCK_GROUP_VARIABLES),
                "for": "block group:*",
                "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS} tract:{tract}",
                "key": key,
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        header, *data = resp.json()
        frames.append(pd.DataFrame(data, columns=header))
    df = pd.concat(frames, ignore_index=True)
    return df.rename(columns=BLOCK_GROUP_VARIABLES)


def _fetch_tract_level(key: str, tracts: list[str]) -> pd.DataFrame:
    resp = httpx.get(
        BASE_URL,
        params={
            "get": ",".join(TRACT_ONLY_VARIABLES),
            "for": "tract:" + ",".join(tracts),
            "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS}",
            "key": key,
        },
        timeout=REQUEST_TIMEOUT_S,
    )
    resp.raise_for_status()
    header, *data = resp.json()
    df = pd.DataFrame(data, columns=header)
    return df.rename(columns=TRACT_ONLY_VARIABLES)


def fetch_raw(tracts: list[str]) -> pd.DataFrame:
    key = _api_key()
    bg = _fetch_block_groups(key, tracts)
    bg["geoid"] = bg["state"] + bg["county"] + bg["tract"] + bg["block group"]

    tr = _fetch_tract_level(key, tracts)
    tr["tract_geoid"] = tr["state"] + tr["county"] + tr["tract"]
    tr = tr.drop(columns=["state", "county", "tract"])

    bg["tract_geoid"] = bg["state"] + bg["county"] + bg["tract"]
    merged = bg.merge(tr, on="tract_geoid", how="left")
    merged["poverty_and_vehicle_are_tract_level"] = True
    return merged


def validate(df: pd.DataFrame) -> None:
    assert len(df) > 0, "no ACS block groups returned"
    assert df["geoid"].notna().mean() > 0.99, "too many block groups missing geoid"
    income = pd.to_numeric(df["median_household_income"], errors="coerce")
    # Census encodes missing/suppressed cells as large negative sentinels (e.g. -666666666).
    assert (income[income >= 0]).between(0, 300_000).mean() > 0.9, (
        "median_household_income outside a plausible range"
    )
    poverty_universe = pd.to_numeric(df["poverty_universe"], errors="coerce")
    assert poverty_universe.notna().mean() > 0.9, "tract-level poverty join failed for too many rows"


def run(force: bool = False) -> Path:
    if not force and is_cached(SOURCE_ID, VERSION):
        return version_dir(SOURCE_ID, VERSION)

    tracts = _target_tracts()
    df = fetch_raw(tracts)
    validate(df)

    vdir = version_dir(SOURCE_ID, VERSION)
    vdir.mkdir(parents=True, exist_ok=True)
    out_path = vdir / "acs5_block_groups.parquet"
    df.to_parquet(out_path)

    write_manifest(
        source=SOURCE_ID,
        version=VERSION,
        url=BASE_URL,
        license=LICENSE,
        files=[out_path],
        bbox_wgs84=None,  # tabular, keyed by block group geoid -- geometry joined from TIGER/Line separately
        extra={
            "row_count": len(df),
            "acs_year": ACS_YEAR,
            "tracts": tracts,
            "note": "poverty (B17001) and vehicle access (B08201) are tract-level, "
            "broadcast to block groups -- not published at block-group precision",
        },
    )
    return vdir


if __name__ == "__main__":
    result_dir = run()
    print(f"census_acs5 cached at {result_dir}")
