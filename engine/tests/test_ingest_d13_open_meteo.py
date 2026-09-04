from __future__ import annotations

import pandas as pd
import pytest
from engine.ingest.d13_open_meteo import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D13 not ingested yet -- run engine.ingest.d13_open_meteo"
)


def test_smoke() -> None:
    df = pd.read_parquet(version_dir(SOURCE_ID, VERSION) / "hourly_summer_2021_2025.parquet")
    assert len(df) > 10_000  # 5 summers of hourly data
    assert df["time"].notna().mean() > 0.99
    temp = pd.to_numeric(df["temperature_2m"], errors="coerce")
    assert temp.between(15, 55).mean() > 0.95
