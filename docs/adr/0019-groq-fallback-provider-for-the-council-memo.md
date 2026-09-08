# 19. A Groq fallback provider for L3, and what it revealed about L6

Date: 2026-09-08

## Status

Accepted

## Context

Mid-build, the Anthropic account's API credit balance ran out (a real,
measured event during this session's own testing of ADR-0018's memo
feature, not a hypothetical). The user asked to add Groq as a working
alternative for now, and to keep both available with an explicit switch
-- not to replace Claude, since ADR-0018 and COOLBLOCK-BUILD-PLAN.md
§7.1 are both explicit that Claude is the intended, headline-sponsor
provider.

Wiring a second provider surfaced two real, unrelated bugs in L6's
provenance guard that Claude's own (much more careful) generations had
never triggered -- both are general correctness fixes, not
Groq-specific workarounds.

## Decision

### 1. A provider abstraction, not a second code path

`engine/narrate/memo.py::_make_caller(provider, client)` returns
`(model_name, call_fn)` for either provider; `generate_council_memo`
itself stays provider-agnostic (payload, prompt, verification, and the
regenerate-once policy are all shared). Selected via `MEMO_LLM_PROVIDER`
(env, default `"anthropic"`) or an explicit `provider=` override, honored
at both layers: `generate_council_memo(payload, provider=...)` and the
API's `POST .../memo?provider=anthropic|groq`. The frontend's
`CouncilMemoPanel` exposes the same choice as a dropdown.

**Model choice**: `openai/gpt-oss-120b` -- the largest general-purpose
text model Groq's tier serves. It is a *reasoning* model: part of
`max_tokens` is spent on hidden reasoning before the visible answer, and
Groq's API for it wants `max_completion_tokens`, not `max_tokens` --
`_make_caller`'s Groq branch uses the right parameter name; `MAX_OUTPUT_TOKENS`
was raised from 2200 to 4000 to leave room for that reasoning overhead
on top of the same ~500-800 word target.

### 2. Bug found: numbers embedded in payload *strings* weren't grounded at all

Before this session, `flatten_numeric_leaves` only walked numeric-typed
JSON leaves. A citation title like "...across 5,723 communities" is a
*string* in the payload -- so a model correctly quoting "5,723" from that
title had nothing to verify against, and L6 flagged a completely
accurate citation as unverifiable. Fixed by also scanning string values
for embedded numbers (`_STRING_EMBEDDED_NUMBER_RE`), with `doi`/`url`
keys excluded (a DOI like `10.1371/journal.pone.0249715` is dense with
digit substrings that would otherwise let an unrelated hallucinated
number "verify" by pure coincidence).

### 3. Bug found: a candidate id's hyphen was misread as a minus sign

A second, subtler bug, caught only once Groq's own text started citing
candidate ids directly (`roof‑02675`): the sign-aware regex used for
*generated text* was reused for scanning *payload strings* too. Applied
to `"roof-02675-cool_roof"`, its leading `[-+]?` matched the ASCII hyphen
before the digits as a unary minus, registering the payload leaf as
**-2675**. Meanwhile the model's own output used a typographic
non-breaking hyphen (U+2011) before the same digits -- which the regex's
sign class doesn't recognize at all -- extracting **+2675** from the
generated text. Two different signs for what should verify as the same
number, entirely an artifact of which hyphen character happened to
precede the digits in each string, not a real discrepancy.

Fixed with a second, sign-free pattern (`_STRING_EMBEDDED_NUMBER_RE`)
used only when scanning *payload* strings; the sign-aware pattern stays
for scanning the *model's* prose, where a genuinely negative number (a
coefficient like -6.95) is a real thing the model might legitimately
state. A hyphen inside an identifier slug is a word separator, never a
minus sign; prose is the only place that distinction matters.

Both bugs are pre-existing, general correctness issues in L6, not
Groq-specific patches -- they were simply never triggered by Claude's
own, more conservative generations, which rarely cite raw candidate ids
or quote exact figures out of a paper title verbatim.

### 4. Groq needs the guard more, not less -- and it works

Measured directly, same payload, same prompt: Claude's first draft had
one hallucinated number (out of ~15), fixed by the one built-in
regeneration. Groq's first draft (before the two fixes above) had up to
14 flagged numbers (out of ~39) -- partly the two false-positive bugs
above, and partly real: Groq did more of its own arithmetic
(inter-site deltas, rounded percentages) despite the prompt's explicit
"do not compute new derived statistics" rule, and once injected outside
knowledge (Phoenix's real but not-in-payload 2030 canopy-goal year) the
prompt explicitly forbade. Added `SYSTEM_PROMPT` rule 7 ("do not use
outside knowledge... if you are not certain a number came from the
payload, leave it out entirely") in response.

After both provenance-guard fixes and the added rule, a full real run
against a real solved scenario (via the actual API endpoint, not just
the library function) converged to **zero unverified numbers, no
regeneration needed, in 3.4 seconds total** -- confirmed working, not
just theorized.

## Consequences

- `pyproject.toml` gained `groq>=0.11` as a normal dependency (parallel
  to `anthropic>=0.39`) -- both providers ship in the same environment;
  nothing is optional-installed or feature-flagged at the packaging
  level, only at the `MEMO_LLM_PROVIDER`/`provider=` call-time switch.
- `.env`'s `MEMO_LLM_PROVIDER=groq` is the *local* default for this
  build right now (Anthropic's balance is exhausted); `.env.example`
  documents both keys and defaults to `"anthropic"` for a fresh clone,
  since that remains the intended, higher-quality provider once a
  credit balance is available.
- The two provenance-guard fixes apply identically to the Anthropic
  path -- Claude-generated memos that happen to quote a citation figure
  or a candidate id benefit from the same corrections, even though
  Claude's own output style triggered neither bug during initial testing.
- Same limitation as ADR-0018: `engine/tests/test_memo_live.py` and
  `apps/api/tests/test_memo_endpoint_live.py` remain gated behind
  `RUN_LLM_TESTS=1` and run against whatever `MEMO_LLM_PROVIDER` is
  currently configured -- they are not parameterized per-provider in
  this pass; running them against both explicitly is a manual, optional
  step (`RUN_LLM_TESTS=1 uv run pytest ... ` with `MEMO_LLM_PROVIDER`
  set either way).
