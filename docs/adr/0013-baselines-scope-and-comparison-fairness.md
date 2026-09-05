# 13. Baselines: shared objective for fairness, disclosed per-baseline candidate pools

Date: 2026-09-05

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §6.5 E5 calls this comparison "the proof the
product works" and sets an explicit bar: "if CoolBlock does not beat
TES-score-only by a clear margin, we have not built anything and we need
to know that on day 5, not day 13." Building it raised two real design
questions.

1. **What metric scores each baseline's selection?** Each baseline
   strategy (spread evenly, worst-first, squeaky wheel, TES-score-only)
   is a different *selection rule*, but they all need to be compared on
   one number. Scoring each with its own internal logic (e.g., "average
   TES score improved") would not be comparable across strategies.
2. **Not every baseline's ranking data covers every candidate.** D7b
   (Census block groups, used for "spread evenly" and "squeaky wheel")
   covers 18 of 23 block groups (`docs/adr/0006-*.md`); D10 (Tree Equity
   Score, used for "TES-score-only") covers 13. A candidate outside a
   given baseline's coverage has no zone/score to rank it by.

## Decision

1. **Every baseline's selection is scored by the same real
   `CoverageObjective.value()`** — D4's EWCB, the exact metric CoolBlock
   itself maximizes (`engine/optimize/objective.py`). This is what makes
   the comparison meaningful: not "which strategy's own preferred metric
   looks best," but "how much of the same real, equity-weighted cooling
   benefit does each strategy's site choice actually produce."
2. **A candidate outside a baseline's zoning/scoring data's coverage is
   simply not selectable by that baseline** — not assigned a guessed
   zone, not silently dropped from the comparison's denominator. This
   mirrors what an actual planner using that specific data source would
   face: someone ranking sites by Tree Equity Score literally cannot rank
   a site TES's own boundaries don't cover. CoolBlock's own solve has no
   such zone dependency and is not artificially constrained to match.
3. **Squeaky wheel is seeded** (`SQUEAKY_WHEEL_SEED`, fixed) for
   reproducibility — a real randomized process, not a hidden one, but one
   that gives the same answer on every rerun so the reported comparison
   number is stable.

## Consequences

- Measured on real data (`docs/METHODOLOGY.md`'s E5 section): CoolBlock
  beats TES-score-only by 4.6x at a $20k budget and 14.0x at $100k, and
  beats every other baseline by a much wider margin -- clearing the
  plan's own bar decisively, not marginally.
- A genuinely informative side-finding: worst-first's total value is
  identical at $20k and $100k -- naive heat-only ranking has no way to
  know that `cool_pavement`/`shade_structure` candidates carry zero EWCB
  attribution in this phase's scope, and impervious surfaces are exactly
  the hottest locations, so most of worst-first's extra budget is spent
  on candidates that cannot score under this objective at all. This is a
  real property of the comparison, not a modeling artifact, and belongs
  in the product's own baseline-comparison screen as an explanation, not
  just a number.
- If D7b or D10's coverage improves in a future phase (e.g., a full-city
  ingest rather than this single-neighborhood bbox), `spread_evenly`,
  `squeaky_wheel`, and `tes_score_only` would automatically gain more
  eligible candidates without any code change -- their eligibility is
  derived from the real data's actual coverage, not a hardcoded list.
