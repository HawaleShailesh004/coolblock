"""Smoke test for D6 (Maricopa County parcels): shape, bounds, null rate.

Requires the cache populated by `uv run python -m engine.ingest.d06_parcels`
(or `make ingest`) -- skipped if it hasn't been run, since this is a network
fetch against a live county service, not something CI should do on every push.
"""

from __future__ import annotations

import pytest
from engine.ingest.d06_parcels import SOURCE_ID, VERSION
from engine.ingest.manifest import is_cached
from engine.tests.ingest_helpers import assert_vector_smoke, load_cached_vector

pytestmark = pytest.mark.skipif(
    not is_cached(SOURCE_ID, VERSION), reason="D6 not ingested yet -- run engine.ingest.d06_parcels"
)


def test_smoke() -> None:
    gdf = load_cached_vector(SOURCE_ID, VERSION, "parcels.parquet")
    assert_vector_smoke(
        gdf,
        required_columns=["APN", "OWNER_NAME", "geometry"],
        min_rows=100,  # Edison-Eastlake is dense; a near-empty result means the bbox is wrong
        null_check_columns=["APN", "geometry"],
    )
