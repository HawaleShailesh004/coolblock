"""L3 -- `build_memo_payload`'s pure computation (derived stats, baseline
uplift). No API cost -- `generate_council_memo` itself (a real Claude
call) is tested separately, gated behind `RUN_LLM_TESTS=1`
(engine/tests/test_memo_live.py)."""

from __future__ import annotations

from typing import Any

import pytest
from engine.narrate.memo import _make_caller, build_memo_payload


def _site(rank: int, cost: float, marginal: float, cumulative_cost: float, cumulative: float) -> dict[str, Any]:
    return {
        "rank": rank,
        "candidate_id": f"c-{rank}",
        "intervention_type": "cool_roof" if rank % 2 else "street_tree",
        "cost_usd": cost,
        "marginal_gain_ewcb": marginal,
        "cumulative_ewcb": cumulative,
        "cumulative_cost_usd": cumulative_cost,
    }


def test_build_memo_payload_computes_derived_stats() -> None:
    sites = [_site(1, 100.0, 50.0, 100.0, 50.0), _site(2, 200.0, 30.0, 300.0, 80.0)]
    payload = build_memo_payload(
        neighborhood_name="Edison-Eastlake",
        city="Phoenix",
        state="AZ",
        plan_name="Test plan",
        budget_usd=1000.0,
        solver="celf",
        sites=sites,
        total_cost_usd=300.0,
        total_ewcb=80.0,
    )
    assert payload["n_sites"] == 2
    assert payload["avg_cost_per_site_usd"] == 150.0
    assert payload["pct_of_budget_used"] == 30.0
    assert payload["intervention_type_counts"] == {"street_tree": 1, "cool_roof": 1}
    assert "baseline_comparison" not in payload


def test_build_memo_payload_includes_methodology_facts_for_the_honesty_rail() -> None:
    payload = build_memo_payload(
        neighborhood_name="Edison-Eastlake", city="Phoenix", state="AZ", plan_name="P",
        budget_usd=1000.0, solver="celf", sites=[], total_cost_usd=0.0, total_ewcb=0.0,
    )
    assert payload["methodology"]["heat_surface_validation_checks_passed"] == 2
    assert payload["methodology"]["heat_surface_validation_checks_total"] == 3


def test_build_memo_payload_computes_baseline_uplift_over_best_other_strategy() -> None:
    payload = build_memo_payload(
        neighborhood_name="Edison-Eastlake", city="Phoenix", state="AZ", plan_name="P",
        budget_usd=1000.0, solver="celf", sites=[], total_cost_usd=0.0, total_ewcb=1000.0,
        baseline_comparison={"spread_evenly": 100.0, "tes_score_only": 250.0, "coolblock": 1000.0},
    )
    assert payload["best_other_strategy_name"] == "tes_score_only"
    assert payload["coolblock_uplift_multiple_over_best_other"] == 4.0


def test_build_memo_payload_top_sites_sorted_by_marginal_gain_descending() -> None:
    sites = [_site(1, 100.0, 10.0, 100.0, 10.0), _site(2, 100.0, 90.0, 200.0, 100.0), _site(3, 100.0, 50.0, 300.0, 150.0)]
    payload = build_memo_payload(
        neighborhood_name="Edison-Eastlake", city="Phoenix", state="AZ", plan_name="P",
        budget_usd=1000.0, solver="celf", sites=sites, total_cost_usd=300.0, total_ewcb=150.0,
    )
    ranks_in_order = [s["rank"] for s in payload["top_sites_by_marginal_ewcb"]]
    assert ranks_in_order == [2, 3, 1]


def test_make_caller_rejects_an_unknown_provider() -> None:
    """No API cost -- this fails before any SDK client is constructed."""
    with pytest.raises(ValueError, match="unknown MEMO_LLM_PROVIDER"):
        _make_caller("openai", None)


def test_make_caller_resolves_anthropic_and_groq_without_a_network_call() -> None:
    """Constructing the client and resolving the model name shouldn't
    itself make a network request -- only `.create()` does, and this test
    never calls it."""
    model, call = _make_caller("anthropic", client=object())
    assert model == "claude-opus-5"
    assert callable(call)

    model, call = _make_caller("groq", client=object())
    assert model == "openai/gpt-oss-120b"
    assert callable(call)
