# CoolBlock — a complete guide

This is a plain-English guide to what CoolBlock is, why it exists, how to
use it, and an honest assessment of how well it actually does the job.
Everything below is either a direct fact about this build or a stated
opinion — the two are labeled so you can tell them apart.

---

## 1. What problem does this solve?

**The problem, stated plainly**: cities know which neighborhoods are
dangerously hot and which residents are most vulnerable to that heat.
That data has been public for years. What doesn't exist is a defensible
way to turn a real budget (a $20,000–$200,000 heat-mitigation grant, the
kind city sustainability offices and neighborhood associations actually
receive) into a specific list of *which* blocks, *which* lots, and
*which* rooftops get the trees, cool roofs, or shade structures.

Today, that decision gets made by:
- a guess,
- whichever resident shows up loudest to a planning meeting (the
  "squeaky wheel"), or
- a generic priority score that doesn't account for what a given budget
  can actually afford or what's actually plantable at each specific site.

**This is an allocation problem, not a data problem.** The heat data,
the vulnerability data, and the literature on what trees/cool-roofs
actually do already exist. Nobody had built the thing that turns all of
that into a ranked, costed, defensible plan for one real neighborhood.
CoolBlock is that thing.

### The bad impact of leaving this unsolved

This isn't a hypothetical harm. The real research this project cites
directly (see §6 below) documents:

- A measured **4.0°C temperature gap** between low-income and
  higher-income blocks in the same city, correlated with a **30% gap in
  tree canopy**.
- Cooling investment that, left to market/political forces alone,
  **accrues disproportionately to higher-income areas** — the same
  people least in danger get the most shade.
- A national gap of roughly **62 million trees** needed to bring
  under-canopied urban areas to equity, with **92% of cities** studied
  showing this same disparity.
- The harm concentrates on exactly the populations (elderly, very
  young, renters, no-vehicle households, people with
  asthma/COPD/heart-disease) this project's own equity weighting is
  built around — that targeting isn't arbitrary; it's the same
  vulnerability profile the cited research uses.

**If this stays unsolved**, the practical consequence isn't neutral —
it's that heat-mitigation money keeps landing where it's politically
easiest to spend it, not where it does the most good, and the
temperature/health gap between rich and poor blocks keeps not closing,
because nobody has the tool to prove a better allocation exists.

---

## 2. What CoolBlock actually does (the real pipeline)

For one real, locked-scope neighborhood (Edison–Eastlake, Phoenix, AZ),
CoolBlock:

1. **Builds a real, measured heat surface** — a 10-meter-resolution
   estimate of land-surface temperature, downscaled from real Landsat
   thermal imagery using a real statistical model (TsHARP), not looked
   up from a table.
2. **Finds every real plantable and retrofittable site** — every
   vacant lot, every parkable margin, every roof that could take a
   cool-roof coating, every parking lot that could take reflective
   pavement — 4,371 real candidate sites in this one neighborhood, each
   with a real estimated cost.
3. **Models what each intervention would actually cool** — a canopy
   cooling kernel *calibrated on this neighborhood's own real data*
   (not just imported from a national average), plus a separate
   real energy-balance model for cool roofs/pavement.
4. **Weights that cooling by who actually benefits** — a real
   equity-weighted objective (the Heat Vulnerability Index: social
   vulnerability, age, asthma/heart-disease prevalence, renter status,
   vehicle access), each factor individually adjustable, not a fixed
   black-box weight.
5. **Solves for the best allocation of your real budget** — a real
   optimization algorithm (CELF, a provably-bounded greedy method),
   cross-checked against an exact solver to confirm it isn't leaving
   value on the table.
6. **Explains the plan in plain English** — an AI-drafted council memo
   whose every number is independently checked against the real
   underlying data before it's shown to you (§7 below).

None of this is simulated for effect. There are no hardcoded results,
no fake progress bars, no placeholder charts. (The one disclosed
exception: a documented "offline demo mode" concept for presenting
without internet — itself built from real cached data, not invented
numbers.)

---

## 3. How to actually use it

1. **Open the app** (`/map`, or click "Open the app"/"Open the live
   instrument" from the homepage).
2. **Look at the map.** The colored surface under the buildings is the
   real, measured heat data (dark purple = cooler, bright orange/yellow
   = hotter — a perceptually accurate color scale, not a misleading
   rainbow). Buildings are real, extruded to their real heights, made
   semi-transparent on purpose so the heat data reads through them.
3. **Toggle layers** on the left (roads, parcels, the Heat Vulnerability
   Index, population, candidate sites, buildings, the heat surface
   itself). Every layer also has a **"View as table"** link — the exact
   same data as a sortable table, for anyone who'd rather read numbers
   than pixels (or needs to, for accessibility).
4. **Adjust the equity weights** (six sliders: Social Vulnerability
   Index, % age 65+, % age <5, asthma+heart-disease prevalence, %
   renter, % no vehicle). Moving a slider changes who counts most in
   the ranking, live, with no server round-trip — you can watch the
   priority map recolor as you argue with the weights.
5. **Choose what you're funding: Trees or Cool roofs.** They're separate
   programs and never ranked against each other. Trees (the default)
   start limited to public land, because that's where a city can plant
   without an owner's permission; cool roofs are mostly private homes.
   At $20,000, the default tree plan is 46 trees across 4 public sites.
6. **Set a budget** and, optionally, **describe constraints in plain
   English** — e.g. *"Keep it to public land only, prioritize sites
   near Booker T Washington School, cap annual maintenance at $8,000."*
   That sentence is parsed by a real AI model into a validated
   configuration; if you name a place, it's looked up against real
   map data and the constraint is applied for real, not just echoed
   back at you.
7. **Click "Run optimizer."** Watch sites land one at a time, in real
   time, as the actual solver runs — this is not a fake progress
   animation; each site that appears is a candidate the algorithm has
   actually just selected.
8. **Read the results**: total sites, total cost, total modeled benefit
   (EWCB — see §6), and the full ranked table (type, cost, marginal
   benefit per site).
9. Click **"Compare vs. baselines"** to see this plan measured against
   four other real allocation strategies (spread evenly, worst-first,
   squeaky-wheel/first-come, and the industry-standard Tree Equity
   Score alone) at the *same* budget — this is the "are we actually
   better than what exists" proof, not a claim taken on faith.
10. Click **"Generate council memo"** for a drafted, plain-English memo
   you could hand to an actual council member — every number in it has
   already been checked against the real data before you see it (amber
   underline = a number that couldn't be verified; this has measured
   0 unverified numbers in real testing).
11. **Export** the plan as GeoJSON or CSV, or generate a **public share
    link** that shows the same solved plan to someone with no login.

---

## 4. Is it enough? (an honest assessment)

**Short answer: it's a real, working, evidence-based prioritization
tool for one real neighborhood — not a finished, universally-deployed
product, and not a guarantee of outcomes.** Specifically, disclosed
plainly (this project has an explicit rule against hiding limitations
until someone finds them):

- **The heat-surface model did not pass its own full validation bar**
  (2 of 3 statistical checks passed, not 3 of 3). Because of that, the
  product is written, everywhere, to call its temperature estimates a
  *"prioritization score,"* never *"predicted cooling."* This is a real
  constraint on how confidently you can quote a specific degree number
  from it — the *ranking* of sites is the trustworthy part; a specific
  decimal-degree promise is not.
- **It covers one neighborhood.** The pipeline is built to be portable
  to a second city via a config change, but that hasn't been done and
  proven yet — so as of today, this is a proof of the *method*, on one
  real place, not yet a multi-city product.
- **Some real-world factors are honestly left out**, not faked: species
  diversity limits, water/irrigation budgets, and wind/aspect effects
  on cooling are all disclosed as *not modeled*, rather than given a
  made-up value.
- **Symbolic/independent-solver verification** (originally planned via
  Wolfram) was built using open substitutes (Python's own `pint` for
  unit-checking, `sympy` for symbolic math, a second independent
  optimizer for cross-checking) rather than the originally-scoped tool,
  because that credential wasn't available — a disclosed substitution,
  not a silently skipped step.

### Is it a *real* solution, or just a demo?

**A real one, within its stated scope.** Every number a user sees is
computed from real public data through a real, inspectable pipeline —
nothing is hardcoded for effect. The "beats the alternatives" claim
(next section) is measured against real baseline strategies on the same
real data, not asserted. The council memo's numbers are independently
checked, not trusted blindly. That said, "real" here means *"a
genuinely computed, honestly-scoped prioritization tool,"* not *"a
validated guarantee that these exact sites will deliver these exact
degrees of cooling."* Those are different claims, and the product is
deliberately worded to only make the first one.

### Is this the best possible way to solve this problem?

**Measured, not just asserted: for the default plan — trees on public
land — CoolBlock delivers 3.4× the equity-weighted cooling benefit of the
best existing approach (ranking sites by Tree Equity Score) at $20,000,
1.4× at $50,000, and 2.5× at $100,000**, at the exact same budget and
choosing from the exact same sites. That's a real, reproducible
measurement, not a marketing number.

On this pool the plan you get is also **provably the best one**: the
optimizer solves the site selection exactly (HiGHS mixed-integer
programming) and proves in about two seconds that no other set of sites
fits the budget and cools more at-risk people. Greedy selection — fast,
and what this ran on until 2026-09-16 — reached only 86% of that at
$20,000 (`docs/adr/0028-*.md`).

An earlier version of this guide quoted 4.6–14×. That number came from
letting trees and cool roofs compete in one ranking, where cool roofs
always won because a roof's surface cooling and a tree's air cooling
aren't the same measurement — the "tree" plan it produced contained zero
trees. Trees and cool roofs are now separate programs that are never
ranked against each other, and the smaller number is the honest one
(`docs/adr/0027-*.md`).

Is it the *theoretical* best possible way? No — and this project says
so rather than claiming otherwise:
- A literal Wolfram-verified independent solve was the original plan;
  an open-source substitute was used instead (see above).
- The plan is proven optimal *given the model* — given these candidate
  sites, these costs, and this estimate of who each tree cools. A proof
  about the model is not a proof about the neighborhood; the heat surface
  it rests on passed 2 of its 3 validation checks.
- The proof holds for pools of up to 1,000 candidate sites, which covers
  the default plan (773). A larger pool — cool roofs on private land, or
  a second neighborhood — falls back to greedy selection, which carries
  only a ~39% worst-case guarantee. The app always says which solver
  produced the plan you are looking at.
- Real-world outcome data (did the trees planted under a CoolBlock plan
  actually measurably cool that block a year later?) doesn't exist yet
  for the obvious reason that no city has planted under this plan yet.
  Every claim this tool makes is a *pre-intervention model*, checked
  against real historical/measured data — not a post-intervention
  result.

**In one sentence**: this is a genuinely real, evidence-based,
honestly-limited tool that demonstrably beats the status quo by a wide
margin on real data — not a finished, infallible, universally-proven
system, and it's built to say so itself rather than let you find out
the hard way.

---

## 5. Where to go for more detail

- `docs/METHODOLOGY.md` — the full technical writeup: every formula,
  every calibration, every disclosed simplification, with the actual
  measured numbers behind each claim in this guide.
- `docs/DATA-SOURCES.md` — exactly which public datasets feed this,
  and their real licenses/currency.
- `docs/adr/` — every significant engineering decision made during this
  build, including the real bugs found and fixed along the way and why
  each judgment call was made.
- `README.md` — current build status: what's done, what's disclosed as
  not done yet.
