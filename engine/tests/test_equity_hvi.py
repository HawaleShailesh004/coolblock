from __future__ import annotations

import numpy as np
import pytest
from engine.equity.hvi import DEFAULT_WEIGHTS, compute_hvi
from engine.ingest import d07_census, d08_svi, d09_places
from engine.ingest.manifest import is_cached

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in (d07_census, d08_svi, d09_places)),
    reason="D7/D8/D9 not all ingested yet",
)


def test_hvi_covers_all_block_groups() -> None:
    hvi = compute_hvi()
    assert len(hvi) > 15
    assert hvi["geoid"].is_unique


def test_hvi_is_finite_and_zero_mean() -> None:
    hvi = compute_hvi()
    assert np.isfinite(hvi["hvi"]).all()
    # Within-neighborhood z-scores average to ~0 by construction.
    assert abs(hvi["hvi"].mean()) < 0.5


def test_hvi_sensitivity_to_weights() -> None:
    """A documented sensitivity check (§6.4 D2): changing which indicator
    dominates should change the ranking, not just rescale it uniformly."""
    equal = compute_hvi(DEFAULT_WEIGHTS)
    svi_only = compute_hvi({"svi": 1.0})
    merged = equal.merge(svi_only, on="geoid", suffixes=("_equal", "_svi_only"))
    # The two weightings should not produce an identical rank ordering.
    assert not merged["hvi_equal"].rank().equals(merged["hvi_svi_only"].rank())
