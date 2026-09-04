from __future__ import annotations

import pytest
from engine.ingest.d10_tree_equity_score import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached
from engine.tests.ingest_helpers import assert_vector_smoke, load_cached_vector

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION),
    reason="D10 not ingested yet -- run engine.ingest.d10_tree_equity_score",
)


def test_smoke() -> None:
    gdf = load_cached_vector(SOURCE_ID, VERSION, "tes_block_groups.parquet")
    assert_vector_smoke(
        gdf,
        required_columns=["GEOID", "tes", "geometry"],
        min_rows=3,
        null_check_columns=["GEOID", "geometry"],
    )
