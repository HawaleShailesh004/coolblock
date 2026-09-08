# 18. The council memo (L3) and its numeric provenance guard (L6)

Date: 2026-09-08

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §7.1 calls for L3 (the council memo) and L6 (the
numeric provenance guard) as load-bearing, non-decorative uses of Claude
-- a MUST-priority item still unbuilt going into this pass. Several real
design decisions had to be made building it.

## Decision

### 1. Citations: the already-curated D16 list, not a pgvector retrieval pipeline

`engine/ingest/d16_literature.py` already registers the five real papers'
titles, venues, DOIs, and *what each one is used for*, and its own
docstring already defers "the chunk/embed pipeline" to Phase 10. At five
documents, handing the model the whole curated list directly in its
context is more reliable than a semantic-search step over a five-row
corpus -- retrieval solves a scale problem this corpus doesn't have.
Building the embed/pgvector pipeline remains genuinely open, not silently
dropped; it would matter once the corpus grows past what fits in context
directly (city planning documents beyond the one Phoenix plan already
registered, say).

### 2. Every derived number is precomputed in Python, not left to the model's arithmetic

`engine.narrate.memo.build_memo_payload` computes `avg_cost_per_site_usd`,
`pct_of_budget_used`, `intervention_type_counts`, and
`coolblock_uplift_multiple_over_best_other` itself, rather than handing
Claude the raw site list and trusting it to compute correct ratios in
generation. Two reasons: LLMs are unreliable at precise arithmetic, and
L6's provenance guard needs every number the model might reasonably state
to actually exist as a literal payload leaf -- if "72% of budget" were
never in the payload, a correct derived statement would be
indistinguishable from a hallucinated one to the guard.

### 3. The honesty rail is a prompt rule, not an inferred convention

`docs/METHODOLOGY.md`'s heat-surface validation gate did not clear all
three checks (2 of 3) -- per §1.4, the product's language must say
"prioritization score," never "predicted cooling," anywhere the heat
surface or the C1 cooling kernel's degree estimates are discussed.
`SYSTEM_PROMPT` states this explicitly as rule #2, and
`METHODOLOGY_FACTS` (a small, hand-maintained constant, kept in sync with
`docs/METHODOLOGY.md` by a human, not parsed from it -- a markdown parser
over a living document is a worse failure mode than a reviewed constant)
gives the model the real numbers to cite if it wants to explain why.
Verified in this session's own first successful generation: the memo
used exactly that language, unprompted beyond the rule.

### 4. L6's provenance guard: regex extraction against every payload leaf, one regeneration, then disclose

`engine/narrate/provenance.py` extracts every numeric token from the
generated text, flattens the entire payload (every nesting level, not
just top-level fields) into a path-keyed map of numbers, and matches each
token within a relative-1%/absolute-0.5 tolerance. Any unmatched number
triggers exactly one regeneration attempt with a corrective system note
naming the offending numbers; if numbers still fail to verify after that,
they are returned to the caller flagged, not hidden or retried forever
(§7.1 L6: "persistent failures are surfaced to the user"). Verified
working, not just implemented: this session's first real generation
required exactly this regeneration path once, for one genuinely
hallucinated number, and the second draft was fully verified.

**A real, disclosed limitation**: matching a number against *any* leaf
in the payload cannot distinguish a correct citation from a coincidental
match against an unrelated field. At this payload's scale (a plan's own
site list plus a handful of methodology constants) that collision risk
is low, not eliminated -- this is a best-effort provenance label for the
UI's hover, not a formal proof of which specific claim a number supports.

### 5. Model routing, cost, and rate limiting

`claude-opus-5` for the memo (§7.1: "quality, run once"), not the
interactive `claude-sonnet-5` used elsewhere in the plan's own routing.
`POST /plans/{id}/scenarios/{version}/memo` is rate-limited harder than
solve/baselines (3/min/workspace) because a real API call -- possibly two,
if L6 triggers a regeneration -- has a real dollar cost. The result is
never persisted or cached server-side; the frontend keeps one generated
memo in component state and only calls the endpoint again if the user
explicitly clicks to regenerate. `include_baselines` (folding in the E5
comparison, §9 ★5) is opt-in for the same reason: it roughly doubles the
endpoint's latency for a section the memo's core sections don't need.

### 6. A real, expected failure mode gets a real error, not a bare 500

`anthropic.APIError` (rate limits, an exhausted credit balance, a
transient outage) is caught explicitly and re-raised as
`HTTPException(502, ...)` with the SDK's own message, rather than
propagating as an opaque 500 the frontend can't act on. This was not a
hypothetical: the account's Claude API credit balance ran out mid-session
while testing this feature, and the 502 path was verified working against
that exact real failure before this ADR was written.

## Consequences

- The memo generation core (`build_memo_payload`, `generate_council_memo`,
  the provenance guard) is proven working end-to-end with a real,
  successful Claude call, made before this session's credit balance ran
  out: correct honesty-rail language, and a real hallucinated number
  caught and corrected by the regeneration path. Further live
  verification (the gated `RUN_LLM_TESTS=1` test suite, and the frontend
  `CouncilMemoPanel`) is blocked on the account's credit balance being
  topped up, not on any known defect.
- `engine/tests/test_memo_live.py` and
  `apps/api/tests/test_memo_endpoint_live.py` are excluded from the
  default `uv run pytest` run (gated behind `RUN_LLM_TESTS=1`) so the
  default test suite never silently spends real API credits; the fast,
  free unit tests (`test_provenance.py`, `test_memo_payload.py`) run
  every time and cover the guard's matching logic and the payload's
  derived-statistic math without touching the network.
- L4 (the grant packet) and L5 (the analyst agent) remain unbuilt --
  explicitly Phase 10/11 COULD-tier work per the plan's own priority
  list, not silently folded into this pass.
