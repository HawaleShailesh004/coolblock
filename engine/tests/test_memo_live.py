"""L3/L6 -- `generate_council_memo` against the real Claude API. Costs a
real API call (opus, up to two calls if the first draft needs a
provenance-guard regeneration) -- skipped by default; set
`RUN_LLM_TESTS=1` to run it (e.g. before a demo, or after touching
`engine/narrate/`). Not part of the default `uv run pytest` suite for the
same reason `docs/adr/0002-*.md` keeps this project's honest about what
runs by default versus what a developer opts into."""

from __future__ import annotations

import os
from typing import Any

import pytest
from engine.narrate.memo import build_memo_payload, generate_council_memo

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LLM_TESTS") != "1",
    reason="costs a real Claude API call -- set RUN_LLM_TESTS=1 to run",
)


def test_generate_council_memo_produces_a_verified_real_memo() -> None:
    sites: list[dict[str, Any]] = [
        {
            "rank": i,
            "candidate_id": f"roof-{i:05d}-cool_roof",
            "intervention_type": "cool_roof",
            "cost_usd": 800.0 + i * 10,
            "marginal_gain_ewcb": 2500.0 - i * 20,
            "cumulative_ewcb": (2500.0 - i * 20) * (i + 1),
            "cumulative_cost_usd": (800.0 + i * 10) * (i + 1),
        }
        for i in range(5)
    ]
    last_cost: float = sites[-1]["cumulative_cost_usd"]
    last_ewcb: float = sites[-1]["cumulative_ewcb"]
    payload = build_memo_payload(
        neighborhood_name="Edison-Eastlake",
        city="Phoenix",
        state="AZ",
        plan_name="Test council plan",
        budget_usd=20000.0,
        solver="celf",
        sites=sites,
        total_cost_usd=last_cost,
        total_ewcb=last_ewcb,
    )

    result = generate_council_memo(payload)

    assert len(result.text) > 200
    assert "EXECUTIVE SUMMARY" in result.text
    # The honesty rail (§1.4): heat-surface/cooling claims must read as a
    # prioritization score, never "predicted cooling."
    assert "predicted cooling" not in result.text.lower()
    assert result.unverified_count == 0, f"unverified numbers survived: {[n for n in result.numbers if not n.verified]}"
