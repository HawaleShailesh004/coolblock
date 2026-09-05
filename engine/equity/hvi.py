"""D2 -- the Heat Vulnerability Index (COOLBLOCK-BUILD-PLAN.md §6.4 D2).

    HVI = z(SVI) + z(%age65+) + z(%age<5) + z(asthma+CHD prevalence)
          + z(%renter) + z(no-vehicle%) + z(1 - AC-access proxy)

Two disclosed adaptations:

1. No AC-access data source is ingested (none exists in the current data
   contract) -- omitted rather than faked with a guessed proxy. HVI here
   is the mean of the six available z-scores, not seven.
2. SVI (D8) and PLACES (D9) are published at *tract* level; this computes
   HVI at *block group* level (D7's granularity, and what Phase 5's
   dasymetric population needs) by broadcasting each tract's value to its
   constituent block groups -- the same approach already used for D7's own
   tract-level poverty/vehicle fields (see engine/ingest/d07_census.py).
3. Z-scores are computed *within this neighborhood's 23 block groups*, not
   against a citywide or national reference population (that would need
   ingesting every Maricopa County block group, out of scope for a
   single-neighborhood tool). HVI here measures *relative* vulnerability
   within Edison-Eastlake, not absolute vulnerability vs. the region --
   stated explicitly in docs/METHODOLOGY.md, not left implicit.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from engine.ingest import d07_census, d08_svi, d09_places
from engine.ingest.manifest import version_dir

# Equal by default -- COOLBLOCK-BUILD-PLAN.md §6.4 D2: "a planner can and
# should argue with them." Exposed as a parameter, not a hardcoded formula,
# so a sensitivity analysis (varying these) is a function call, not a rewrite.
DEFAULT_WEIGHTS: dict[str, float] = {
    "svi": 1.0,
    "pct_age65_plus": 1.0,
    "pct_age_under5": 1.0,
    "asthma_chd_prevalence": 1.0,
    "pct_renter": 1.0,
    "pct_no_vehicle": 1.0,
}

_MALE_65_COLS = [f"male_65_{n}" for n in range(20, 26)]
_FEMALE_65_COLS = [f"female_65_{n}" for n in range(44, 50)]


def _zscore(s: pd.Series) -> pd.Series:
    std = s.std()
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / std


def load_block_group_indicators() -> pd.DataFrame:
    """Raw indicator values per block group -- before z-scoring, so the
    sensitivity analysis notebook can inspect them directly."""
    acs = pd.read_parquet(version_dir(d07_census.SOURCE_ID, d07_census.VERSION) / "acs5_block_groups.parquet")
    for col in [*_MALE_65_COLS, *_FEMALE_65_COLS, "male_under5", "female_under5", "total_population",
                "renter_occupied", "occupied_housing_units", "households_no_vehicle", "households_total"]:
        acs[col] = pd.to_numeric(acs[col], errors="coerce")

    acs["age65_plus"] = acs[_MALE_65_COLS + _FEMALE_65_COLS].sum(axis=1)
    acs["age_under5"] = acs["male_under5"] + acs["female_under5"]
    acs["pct_age65_plus"] = acs["age65_plus"] / acs["total_population"]
    acs["pct_age_under5"] = acs["age_under5"] / acs["total_population"]
    acs["pct_renter"] = acs["renter_occupied"] / acs["occupied_housing_units"]
    acs["pct_no_vehicle"] = acs["households_no_vehicle"] / acs["households_total"]

    svi = gpd.read_parquet(version_dir(d08_svi.SOURCE_ID, d08_svi.VERSION) / "svi_tracts.parquet")
    svi_by_tract = svi.set_index("FIPS")["RPL_THEMES"].replace(-999, np.nan)

    places = pd.read_parquet(version_dir(d09_places.SOURCE_ID, d09_places.VERSION) / "places_tracts.parquet")
    places["casthma_crudeprev"] = pd.to_numeric(places["casthma_crudeprev"], errors="coerce")
    places["chd_crudeprev"] = pd.to_numeric(places["chd_crudeprev"], errors="coerce")
    places_by_tract = (places.set_index("tractfips")["casthma_crudeprev"]
                        + places.set_index("tractfips")["chd_crudeprev"])

    acs["svi"] = acs["tract_geoid"].map(svi_by_tract)
    acs["asthma_chd_prevalence"] = acs["tract_geoid"].map(places_by_tract)

    return acs[[
        "geoid", "tract_geoid", "total_population", "svi", "pct_age65_plus", "pct_age_under5",
        "asthma_chd_prevalence", "pct_renter", "pct_no_vehicle",
    ]]


def compute_hvi(weights: dict[str, float] | None = None) -> pd.DataFrame:
    weights = weights or DEFAULT_WEIGHTS
    df = load_block_group_indicators().copy()

    z_cols = []
    for indicator, weight in weights.items():
        z_col = f"z_{indicator}"
        df[z_col] = _zscore(df[indicator]) * weight
        z_cols.append(z_col)

    df["hvi"] = df[z_cols].mean(axis=1)
    return df[["geoid", "tract_geoid", "total_population", *z_cols, "hvi"]]
