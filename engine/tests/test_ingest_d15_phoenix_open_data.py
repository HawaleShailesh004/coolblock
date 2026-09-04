from __future__ import annotations

import pytest
from engine.ingest.d15_phoenix_open_data import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached
from engine.tests.ingest_helpers import assert_vector_smoke, load_cached_vector

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION),
    reason="D15 not ingested yet -- run engine.ingest.d15_phoenix_open_data",
)


def test_smoke() -> None:
    gdf = load_cached_vector(SOURCE_ID, VERSION, "shade_plan_tracts.parquet")
    assert_vector_smoke(
        gdf,
        required_columns=["GEOID_num", "avgLST_F_0", "tree_pct", "geometry"],
        min_rows=3,
        null_check_columns=["GEOID_num", "geometry"],
    )
