from __future__ import annotations

import pandas as pd
import pytest
from engine.ingest.d14_nasa_power import FILL_VALUE, SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D14 not ingested yet -- run engine.ingest.d14_nasa_power"
)


def test_smoke() -> None:
    df = pd.read_parquet(version_dir(SOURCE_ID, VERSION) / "daily_summer_2021_2025.parquet")
    assert len(df) > 500  # 5 summers of daily data
    assert df["date"].notna().mean() > 0.99
    irradiance = pd.to_numeric(df["ALLSKY_SFC_SW_DWN"].replace(FILL_VALUE, pd.NA), errors="coerce")
    assert irradiance.between(3, 12).mean() > 0.9
