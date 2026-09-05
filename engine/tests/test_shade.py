from __future__ import annotations

import pandas as pd
import pytest
from engine.impact.shade import (
    DESIGN_DAY_END_HOUR,
    DESIGN_DAY_START_HOUR,
    _shadow_polygon,
    compute_shade_hours,
    find_design_day,
    load_pedestrian_surfaces,
    run_shade_raytrace,
    solar_positions,
)
from engine.ingest import d04_osm, d13_open_meteo
from engine.ingest.manifest import is_cached, version_dir
from engine.surface.candidates import generate_candidates
from shapely.geometry import Point

pytestmark = pytest.mark.skipif(
    not all(is_cached(src.SOURCE_ID, src.VERSION) for src in (d04_osm, d13_open_meteo)),
    reason="D4/D13 not all ingested yet",
)


def test_design_day_is_the_real_hottest_day_on_record() -> None:
    df = pd.read_parquet(
        version_dir(d13_open_meteo.SOURCE_ID, d13_open_meteo.VERSION) / "hourly_summer_2021_2025.parquet"
    )
    df["temperature_2m"] = pd.to_numeric(df["temperature_2m"], errors="coerce")
    expected_max = df["temperature_2m"].max()

    design_day = find_design_day()
    assert design_day.max_temperature_c == pytest.approx(expected_max)
    assert len(design_day.hours) == DESIGN_DAY_END_HOUR - DESIGN_DAY_START_HOUR + 1


def test_solar_elevation_peaks_near_midday() -> None:
    design_day = find_design_day()
    sun = solar_positions(design_day)
    peak_hour = sun["apparent_elevation"].idxmax().hour
    assert 11 <= peak_hour <= 14


def test_shadow_polygon_none_when_sun_below_horizon() -> None:
    center = Point(0, 0)
    assert _shadow_polygon(center, 8.0, 8.0, azimuth_deg=90.0, elevation_deg=-5.0) is None
    assert _shadow_polygon(center, 8.0, 8.0, azimuth_deg=90.0, elevation_deg=0.0) is None


def test_shadow_polygon_points_away_from_sun() -> None:
    """A sun due east (azimuth 90) should cast a shadow extending west --
    negative x -- from the source point."""
    center = Point(0, 0)
    shadow = _shadow_polygon(center, height_m=8.0, width_m=8.0, azimuth_deg=90.0, elevation_deg=45.0)
    assert shadow is not None
    minx, _miny, maxx, _maxy = shadow.bounds
    assert maxx <= 0.1  # the shadow lies on the -x side of the source


def test_shade_hours_bounded_by_design_day_length() -> None:
    candidates = generate_candidates()
    scored, design_day = run_shade_raytrace(candidates)
    assert (scored["shade_hours_delivered"] >= 0).all()
    assert (scored["shade_hours_delivered"] <= len(design_day.hours)).all()


def test_pedestrian_surfaces_include_real_sidewalks_and_bus_stops() -> None:
    candidates = generate_candidates()
    surfaces = load_pedestrian_surfaces(str(candidates.crs))
    assert len(surfaces) > 0
    assert "sidewalk_or_crossing" in surfaces["surface_type"].to_numpy()


def test_compute_shade_hours_matches_run_shade_raytrace() -> None:
    """A regression guard on the two entry points staying consistent."""
    candidates = generate_candidates().head(20)
    design_day = find_design_day()
    sun = solar_positions(design_day)
    surfaces = load_pedestrian_surfaces(str(candidates.crs))
    direct = compute_shade_hours(candidates, surfaces, sun)

    scored, _ = run_shade_raytrace(candidates)
    pd.testing.assert_series_equal(
        direct["shade_hours_delivered"], scored["shade_hours_delivered"], check_names=False
    )
