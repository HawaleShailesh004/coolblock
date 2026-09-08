"""L6 -- the numeric provenance guard. Pure logic, no API cost."""

from __future__ import annotations

from engine.narrate.provenance import flatten_numeric_leaves, verify_numbers


def test_flatten_numeric_leaves_walks_nested_dicts_and_lists() -> None:
    payload = {"budget_usd": 50000.0, "sites": [{"cost_usd": 807.45}, {"cost_usd": 1200}], "solver": "celf"}
    leaves = flatten_numeric_leaves(payload)
    assert leaves["$.budget_usd"] == 50000.0
    assert leaves["$.sites[0].cost_usd"] == 807.45
    assert leaves["$.sites[1].cost_usd"] == 1200.0
    assert "$.solver" not in leaves  # a string, not a number


def test_flatten_numeric_leaves_excludes_booleans() -> None:
    leaves = flatten_numeric_leaves({"public_land_only": True, "count": 3})
    assert "$.public_land_only" not in leaves
    assert leaves["$.count"] == 3.0


def test_flatten_numeric_leaves_finds_numbers_embedded_in_string_values() -> None:
    payload = {"citations": {"papers": [{"title": "A study across 5,723 communities", "doi": "10.1371/journal.pone.0249715"}]}}
    leaves = flatten_numeric_leaves(payload)
    assert 5723.0 in leaves.values()
    # the DOI's own digits must not leak in as verifiable numbers --
    # otherwise a hallucinated "1371" or "249715" would coincidentally verify.
    assert 1371.0 not in leaves.values()
    assert 249715.0 not in leaves.values()


def test_verify_numbers_grounds_a_number_quoted_from_a_citation_title() -> None:
    payload = {
        "citations": {"papers": [{"title": "A study across 5,723 communities", "doi": "10.1371/journal.pone.0249715"}]}
    }
    matches = verify_numbers("This finding echoes a study of 5,723 communities.", payload)
    assert all(m.verified for m in matches)


def test_verify_numbers_grounds_a_candidate_id_across_different_hyphen_characters() -> None:
    """Regression test for a real bug: a candidate id's ASCII hyphen
    ("roof-02675-cool_roof") was previously misread as a unary minus when
    scanning payload strings, registering the leaf as -2675. A model
    quoting the same id with a typographic non-breaking hyphen
    ("roof‑02675", U+2011 -- which the generated-text regex, unlike the
    payload-string one, still treats as sign-less since ‑ isn't in its
    character class either) extracted +2675 from its own text -- two
    different signs for what should verify as the same number."""
    payload = {"sites": [{"candidate_id": "roof-02675-cool_roof"}]}
    matches = verify_numbers("The top site (roof‑02675) was selected first.", payload)
    assert len(matches) == 1
    assert matches[0].value == 2675.0
    assert matches[0].verified is True


def test_verify_numbers_matches_a_number_present_in_the_payload() -> None:
    payload = {"budget_usd": 50000.0, "n_sites": 27}
    matches = verify_numbers("We recommend spending $50,000 across 27 sites.", payload)
    assert all(m.verified for m in matches)
    budget_match = next(m for m in matches if m.value == 50000.0)
    assert budget_match.path == "$.budget_usd"


def test_verify_numbers_flags_a_number_absent_from_the_payload() -> None:
    payload = {"budget_usd": 50000.0}
    matches = verify_numbers("The plan costs $999,999 in total.", payload)
    assert len(matches) == 1
    assert matches[0].verified is False
    assert matches[0].path is None


def test_verify_numbers_respects_relative_tolerance_for_large_values() -> None:
    payload = {"total_ewcb": 110170.57}
    # off by less than 1%
    matches = verify_numbers("The total modeled benefit was 110,200.", payload)
    assert matches[0].verified is True


def test_verify_numbers_rejects_values_outside_tolerance() -> None:
    payload = {"total_ewcb": 110170.57}
    # off by more than 1% and more than the absolute floor
    matches = verify_numbers("The total modeled benefit was 130,000.", payload)
    assert matches[0].verified is False
