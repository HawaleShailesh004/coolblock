from __future__ import annotations

import numpy as np
import pytest
from engine.equity.exposure import (
    BUS_STOP_EXPOSURE_MULTIPLIER,
    SCHOOL_EXPOSURE_MULTIPLIER,
    compute_exposure_multiplier,
)
from engine.equity.population import redistribute_population
from engine.ingest import d04_osm, d07_census, d07b_tiger_bg
from engine.ingest.manifest import is_cached

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in (d04_osm, d07_census, d07b_tiger_bg)),
    reason="D4/D7/D7b not all ingested yet",
)


def test_exposure_multiplier_is_bounded_and_at_least_one() -> None:
    buildings = redistribute_population()
    exposure = compute_exposure_multiplier(buildings)
    assert (exposure >= 1.0).all()
    max_possible = BUS_STOP_EXPOSURE_MULTIPLIER * SCHOOL_EXPOSURE_MULTIPLIER
    assert (exposure <= max_possible + 1e-9).all()


def test_exposure_multiplier_varies_across_real_buildings() -> None:
    """Not every building should get the same multiplier -- real proximity
    to real bus stops/schools should produce real variation."""
    buildings = redistribute_population()
    exposure = compute_exposure_multiplier(buildings)
    assert len(np.unique(exposure)) > 1
