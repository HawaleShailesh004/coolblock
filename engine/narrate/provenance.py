"""L6 -- the numeric provenance guard (COOLBLOCK-BUILD-PLAN.md §7.1 L6):

"Every number appearing in generated prose is extracted post-generation
by regex, and each must match a value present in the source payload
within tolerance. Unmatched numbers trigger a flagged regeneration;
persistent failures are surfaced to the user... Numbers that do verify
are rendered with a hover showing their provenance path."

This module does the extraction and matching; `engine.narrate.memo` owns
the regenerate-once-then-flag policy on top of it.

**What counts as "in the payload."** The payload passed to
`verify_numbers` is the exact JSON-serializable dict handed to the model
as its data -- every numeric leaf, at any nesting depth, is a legitimate
source for a number to trace back to (`plan.sites[3].cost_usd`, not just
top-level fields). A generated number matches if it's within tolerance of
*any* leaf, so the model narrating "the fourth site cost $807" is
verified against `sites[3].cost_usd`, regardless of where in its own
prose that number appears.

**A real, disclosed limitation**: this cannot distinguish "the model
correctly cited a number" from "the model stated an unrelated number that
happens to coincide with something else in the payload" (e.g. a
coincidental match between a site's rank and an unrelated cost). At this
payload's scale (a few dozen numeric leaves) that collision risk is low,
not eliminated -- exact provenance-path attribution is a best-effort
label for the UI's hover, not a formal proof of *which* claim a number
supports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Matches: optional sign, optional '$', digit groups with optional commas,
# optional decimal part, optional trailing '%' or 'x' (e.g. "4.6x", "25%").
# Deliberately over-inclusive (a bare "3" in "Phase 3" also matches) --
# false-positive *candidates* here just get checked against the payload
# like anything else; the cost of a miss is silent overclaiming, so this
# guard errs toward flagging too much, not too little.
_NUMBER_RE = re.compile(r"[-+]?\$?\d[\d,]*(?:\.\d+)?%?x?\b")

# Same shape, minus the leading sign -- used only when scanning *payload
# string values* (titles, slugs, ids) for embedded numbers, never on the
# model's own generated prose. Real bug this closes: a candidate id like
# "roof-02675-cool_roof" has its ASCII hyphen misread as a unary minus by
# the sign-aware regex, registering the payload leaf as -2675 -- while the
# model's own generated text (which typographically upgrades the hyphen to
# a non-breaking one, U+2011, that the sign-aware regex doesn't recognize
# as a sign character at all) extracts +2675 from its own citation of the
# same id. Two different values for what should be the same number, purely
# from which hyphen character happened to precede the digits, causing a
# real id-cite to fail verification. A hyphen inside an identifier slug is
# a word separator, never a minus sign -- prose is the only place a
# genuinely negative number needs the sign-aware pattern.
_STRING_EMBEDDED_NUMBER_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?x?\b")

REL_TOLERANCE = 0.01  # 1% relative
ABS_TOLERANCE = 0.5  # for small numbers where 1% is too tight to be meaningful


@dataclass(frozen=True)
class NumberMatch:
    raw: str
    value: float
    start: int
    end: int
    verified: bool
    path: str | None  # dotted/bracketed JSON path into the payload, e.g. "sites[3].cost_usd" -- None if unverified


def _parse_numeric_token(raw: str) -> float | None:
    cleaned = raw.rstrip("%x").replace(",", "").replace("$", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


# Keys never scanned for embedded numbers even though they're strings --
# identifiers like a DOI (`10.1371/journal.pone.0249715`) are dense with
# digit substrings that would otherwise "verify" an unrelated hallucinated
# number purely by coincidence (a real false-negative risk found while
# testing this guard against a second model provider -- see
# docs/adr/0019-*.md).
_SKIP_STRING_KEYS = {"doi", "url"}


def flatten_numeric_leaves(payload: Any, path: str = "$", _key: str | None = None) -> dict[str, float]:
    """Every numeric leaf in `payload`, keyed by its JSON path -- including
    numbers embedded *inside* string values (a citation title like "...
    across 5,723 communities" legitimately grounds the model quoting
    "5,723," even though that number is text, not a JSON number, in the
    payload). Booleans are excluded (Python's `bool` is a subtype of
    `int`, and `True`/`False` are never a "number" a memo would
    legitimately cite as one); `doi`/`url` string fields are excluded
    (see `_SKIP_STRING_KEYS`)."""
    leaves: dict[str, float] = {}
    if isinstance(payload, bool):
        return leaves
    if isinstance(payload, int | float):
        leaves[path] = float(payload)
    elif isinstance(payload, str):
        if _key is not None and _key.lower() in _SKIP_STRING_KEYS:
            return leaves
        for m in _STRING_EMBEDDED_NUMBER_RE.finditer(payload):
            value = _parse_numeric_token(m.group())
            if value is not None:
                leaves.setdefault(f"{path}::text@{m.start()}", value)
    elif isinstance(payload, dict):
        for key, value in payload.items():
            leaves.update(flatten_numeric_leaves(value, f"{path}.{key}", _key=key))
    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            leaves.update(flatten_numeric_leaves(value, f"{path}[{i}]", _key=_key))
    return leaves


def _find_matching_path(value: float, known: dict[str, float]) -> str | None:
    for path, known_value in known.items():
        tolerance = max(ABS_TOLERANCE, abs(known_value) * REL_TOLERANCE)
        if abs(value - known_value) <= tolerance:
            return path
    return None


def verify_numbers(text: str, payload: dict[str, Any]) -> list[NumberMatch]:
    """Extracts every numeric token from `text` and checks it against
    every numeric leaf in `payload`. Returns one `NumberMatch` per token,
    in order of appearance, whether or not it verified."""
    known = flatten_numeric_leaves(payload)
    matches: list[NumberMatch] = []
    for m in _NUMBER_RE.finditer(text):
        value = _parse_numeric_token(m.group())
        if value is None:
            continue
        path = _find_matching_path(value, known)
        matches.append(NumberMatch(raw=m.group(), value=value, start=m.start(), end=m.end(), verified=path is not None, path=path))
    return matches
