"""Smoke test for D7 (Census ACS 5-year). Tabular, no geometry."""

from __future__ import annotations

import pandas as pd
import pytest
from engine.ingest.d07_census import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D7 not ingested yet -- run engine.ingest.d07_census"
)


def test_smoke() -> None:
    df = pd.read_parquet(version_dir(SOURCE_ID, VERSION) / "acs5_block_groups.parquet")
    assert len(df) >= 3
    assert df["geoid"].notna().mean() > 0.99

    income = pd.to_numeric(df["median_household_income"], errors="coerce")
    assert (income[income >= 0]).between(0, 300_000).mean() > 0.9

    poverty_universe = pd.to_numeric(df["poverty_universe"], errors="coerce")
    assert poverty_universe.notna().mean() > 0.9
