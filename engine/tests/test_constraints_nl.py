"""L1 -- NL -> optimizer constraints. Pure-logic tests run for free against
the real cached OSM amenities export and the real cached candidate
universe (no LLM call); the end-to-end tool-use loop against a real model
is gated behind RUN_LLM_TESTS=1, same pattern as engine/tests/test_memo_live.py."""

from __future__ import annotations

import os

import pytest
from engine.narrate.constraints_nl import (
    ParsedConstraints,
    PlaceResolution,
    _build_place_resolutions,
    nearby_candidate_ids,
    parse_constraints,
    resolve_place,
)


def test_resolve_place_finds_a_real_school_by_partial_name() -> None:
    result = resolve_place("Booker T Washington")
    assert result["found"] is True
    assert result["matched_name"] == "Booker T Washington School"
    # Real Phoenix, AZ coordinates (WGS84), not the amenities parquet's
    # native UTM-zone-12N meters -- the bug this test guards against.
    assert 33.0 < result["lat"] < 34.0
    assert -113.0 < result["lon"] < -111.0


def test_resolve_place_discloses_not_found_rather_than_matching_an_unrelated_place() -> None:
    result = resolve_place("Nonexistent Imaginary School That Does Not Exist")
    assert result["found"] is False


def test_nearby_candidate_ids_finds_real_sites_near_a_real_resolved_school() -> None:
    school = resolve_place("Booker T Washington")
    result = nearby_candidate_ids(school["lat"], school["lon"], radius_m=300)
    assert result["count"] > 0
    assert all(isinstance(cid, str) and cid for cid in result["candidate_ids"])


def test_nearby_candidate_ids_finds_nothing_far_out_in_the_ocean() -> None:
    result = nearby_candidate_ids(0.0, 0.0, radius_m=300)
    assert result == {"candidate_ids": [], "count": 0, "radius_m": 300}


def test_parsed_constraints_accepts_a_well_formed_submission() -> None:
    constraints = ParsedConstraints.model_validate(
        {
            "public_land_only": True,
            "annual_maintenance_cap_usd": 8000,
            "mandatory_include_ids": ["roof-00299-cool_roof"],
        }
    )
    assert constraints.public_land_only is True
    assert constraints.annual_maintenance_cap_usd == 8000
    assert constraints.max_sites_per_zone is None
    assert constraints.unsupported_requests == []


def test_build_place_resolutions_pairs_a_resolve_and_its_matching_nearby_call() -> None:
    tool_log = [
        {"tool": "resolve_place", "input": {"name": "X"}, "result": {"found": True, "query": "X", "matched_name": "X School", "lat": 33.4, "lon": -112.0}},
        {"tool": "nearby_candidate_ids", "input": {"lat": 33.4, "lon": -112.0, "radius_m": 300}, "result": {"candidate_ids": ["a", "b"], "count": 2, "radius_m": 300}},
    ]
    resolutions = _build_place_resolutions(tool_log)
    assert resolutions == [PlaceResolution(query="X", found=True, matched_name="X School", lat=33.4, lon=-112.0, candidate_ids=["a", "b"])]


def test_build_place_resolutions_reports_an_unfound_place_with_no_candidates() -> None:
    tool_log = [{"tool": "resolve_place", "input": {"name": "Y"}, "result": {"found": False, "query": "Y"}}]
    resolutions = _build_place_resolutions(tool_log)
    assert resolutions == [PlaceResolution(query="Y", found=False)]


pytestmark_live = pytest.mark.skipif(
    os.environ.get("RUN_LLM_TESTS") != "1",
    reason="costs a real LLM API call -- set RUN_LLM_TESTS=1 to run",
)


@pytestmark_live
def test_parse_constraints_resolves_a_real_place_and_flags_an_unsupported_request() -> None:
    result = parse_constraints(
        "Keep it to public land only, prioritize sites near Booker T Washington School, "
        "cap annual maintenance at $8,000, and no more than 20% of one tree species."
    )
    assert result.constraints.public_land_only is True
    assert result.constraints.annual_maintenance_cap_usd == 8000
    assert len(result.constraints.mandatory_include_ids) > 0
    assert len(result.constraints.unsupported_requests) > 0  # the species cap has no real field
    assert any(r.found and r.candidate_ids for r in result.place_resolutions)


@pytestmark_live
def test_parse_constraints_discloses_an_unresolvable_place_instead_of_inventing_one() -> None:
    result = parse_constraints("Prioritize sites near Xyzzyplonk Elementary, a school that does not exist.")
    assert not result.constraints.mandatory_include_ids
    assert any(not r.found for r in result.place_resolutions) or result.constraints.unsupported_requests
