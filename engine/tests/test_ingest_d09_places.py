"""Smoke test for D9 (CDC PLACES). Tabular, no geometry -- doesn't use the
shared vector smoke helper, which assumes a GeoDataFrame with a CRS."""

from __future__ import annotations

import pandas as pd
import pytest
from engine.ingest.d09_places import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached, version_dir

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D9 not ingested yet -- run engine.ingest.d09_places"
)


def test_smoke() -> None:
    df = pd.read_parquet(version_dir(SOURCE_ID, VERSION) / "places_tracts.parquet")
    assert len(df) >= 3
    assert "tractfips" in df.columns
    assert df["tractfips"].notna().mean() > 0.99
    rate = pd.to_numeric(df["casthma_crudeprev"], errors="coerce")
    assert rate.between(0, 100).mean() > 0.95
