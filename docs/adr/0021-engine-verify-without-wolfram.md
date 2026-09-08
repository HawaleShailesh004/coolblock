# 21. `engine.verify`, built against the no-Wolfram fallback

Date: 2026-09-08

## Status

Accepted

## Context

`docs/adr/0002-*.md`, decided at Phase 0, already recorded that a Wolfram
Cloud credential was not in hand and that §7.2 would drop to its
documented fallback: *"a second, independent Python solver in place of
the Wolfram `NMaximize` cross-check"* -- and committed to something more
specific than "skip it": *"`engine.verify` must be written against an
interface that tolerates a missing Wolfram credential without failing the
rest of the pipeline -- checked at Phase 6/10 rather than assumed."*

Two of §7.2's three asks had already been partially met by Phase 6,
informally:

- The independent-solver cross-check (§7.2.3) existed as a real
  measurement -- CELF greedy reaches 99.6-99.9% of HiGHS's proven exact
  optimum on the real candidate universe (`docs/METHODOLOGY.md`'s "E2
  (second solver)" table) -- but only as a notebook run once by hand, not
  as code that runs again on demand or in CI.
- The unit check (§7.2.1) existed as a *manual*, hand-written proof in
  `engine/impact/albedo.py`'s own module docstring ("Manual unit check
  (Wolfram MCP not available this session)... Dimensionally consistent")
  -- correct, but a comment a future edit could silently invalidate
  without anyone noticing.
- The symbolic sensitivity ask (§7.2.2) had not been addressed at all:
  `docs/METHODOLOGY.md` asserts beta's confidence interval propagates
  "linearly" into ΔT_peak's own interval, without deriving that linearity
  anywhere.

Offered the choice again this session (a real Wolfram Cloud credential
would unblock the literal Wolfram Language integration), the answer was
that no Wolfram Cloud credential is available, so this closes out §7.2
via the same fallback ADR-0002 already committed to -- not a new
decision, a completion of one already made.

## Decision

`engine/verify/` now has three real modules, each substituting a specific
non-Wolfram tool for the specific Wolfram capability the plan named, and
each with tests that exercise real inputs (cached project data, not
placeholder numbers):

1. **`optimizer_crosscheck.py`** (§7.2.3, `NMaximize` vs CP-SAT ->
   `engine.optimize.celf` vs `engine.optimize.exact`/HiGHS). Formalizes
   the notebook measurement as `cross_check_optimizer()`, callable on any
   `CoverageObjective`. `engine/tests/test_optimizer_crosscheck.py`
   includes a real-candidate-universe test reproducing the documented
   99.6% figure automatically, plus a deliberately-adversarial small
   instance proving the check can detect real disagreement, not just
   agreement -- the same "prove it can fail" discipline as
   `engine/tests/test_local_search.py`'s deliberately-improving swap.

2. **`units.py`** (§7.2.1, Wolfram `Quantity[]` -> `pint`). Independently
   re-implements C3's energy-balance ΔT formula with every quantity
   carrying a real, enforced unit; `pint.DimensionalityError` fires if an
   operation is unit-incompatible, promoting `engine/impact/albedo.py`'s
   existing hand-written manual check into code that actually enforces
   the same claim rather than asserting it in prose. Tested for
   numeric agreement with the production formula's real constants *and*
   for actually catching a deliberately-constructed real unit error
   (adding W/m² directly to W/(m²·K)) -- not merely passing by
   construction.

3. **`sensitivity.py`** (§7.2.2, Wolfram `D`/`Solve` -> `sympy`). Derives
   d(ΔT_peak)/d(beta) from the actual `beta*f*g*h` expression via
   `sympy.diff`, confirms the result really is the constant `f*g*h` with
   no remaining beta term (i.e. the relationship genuinely is linear, not
   assumed to be), and uses that real derivative to propagate C1's OLS
   confidence interval on beta into a real interval on ΔT_peak. Tested
   against `calibrate_beta()`'s real, cached-data calibration -- not a
   synthetic beta.

## Consequences

- `pyproject.toml` gained `pint>=0.24` (installed fresh) and `sympy>=1.13`
  (already present transitively; now a direct, explicit dependency since
  this project relies on it directly).
- `WOLFRAM_APP_ID` in `.env.example` remains documented and unset; if a
  real Wolfram Cloud credential is added later, these three modules are
  exactly where a literal Wolfram Language implementation would replace
  the `pint`/`sympy`/HiGHS substitutes -- the module docstrings each say
  precisely which Wolfram capability they stand in for, so that swap (if
  it ever happens) has a clear, pre-identified target rather than
  starting from scratch.
- None of this sits on the demo path (matching §7.2's own "every Wolfram
  call is cached; the API is never on the demo path") -- no new API
  endpoint or UI surface was added; this is internal engineering
  verification, exercised by the test suite (`uv run pytest engine/tests`),
  the same way `engine/tests/test_exact.py` and `test_local_search.py`
  already verify E2's other two solvers.
- This closes the one remaining SHOULD-tier item in Phase 10's own scope
  (`README.md`, `docs/adr/0019-*.md`, `docs/adr/0020-*.md` cover L3/L6 and
  L1 respectively) -- L2, L4, and L5 remain explicitly COULD-tier/roadmap-
  only per §12.1, not built in this pass.
