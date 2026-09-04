# NextStep Hacks 2026 — Win-Optimized Strategy Brief

**Target:** https://nextstep2026.devpost.com/
**Theme:** "Earth Forward" — environmental problems solved with technology
**Deadline:** Sep 13, 2026 @ 5:00pm EDT
**Analysis date:** Sep 3, 2026 — **10 days remain**
**Prepared for:** an LLM-augmented solo/small-team builder

---

## ⚠️ Read this first — two facts that reframe everything

**1. You have 10 days, not 30–90.** The event opened Aug 21. You are entering with ~43% of
the window already gone. Every recommendation below is scoped to a 10-day build by an
LLM-augmented builder, not a standard hackathon runway.

**2. This is a small pond, and that is the whole opportunity.**

| Year | Registered | Submitted | Conversion |
|---|---|---|---|
| 2025 | 885 | **98** | 11.1% |
| 2026 | 504 | **~50–70 (projected)** | ~11–14% |

At 504 registrants, expect **50–70 submissions**. Three cash prizes against ~56 entries means
**a top-3 finish is roughly the top 5%** — not the top 0.3% you'd need at a 1,000-submission
corporate hackathon. This is one of the highest expected-value hackathons you could enter
right now. Do not treat it as a lottery. Treat it as winnable.

---

# PHASE 1 — HACKATHON INTELLIGENCE BRIEF

## 1a. Theme decoding

**Surface reading:** "Build something environmental." Named sub-domains are climate
resilience, renewable energy, conservation, sustainable agriculture, waste reduction.

**What it is actually asking for.** Two lines in the theme statement do the real work:

> "identify a pressing environmental problem affecting **your community** or the world"

> "We encourage you to **collaborate with local organizations, environmental groups,
> researchers, or community members** to ensure your solution addresses **real-world needs**."

Combined with the Adherence criterion — *"Does it implement this theme **fully** or just
partially?"* — the organizers are signalling that a generic global-abstraction project scores
as "partial." A project anchored to a **specific, named place and a specific, named group of
people** scores as "full." This is the cheapest scoring point in the entire rubric and most
teams will miss it.

**What the tracks reveal:** There are **no sub-tracks.** One theme, one pool, one ranking.
That means no track-selection arbitrage in the usual sense — but it also means every
submission is compared directly against every other, so differentiation carries the entire
burden.

**Disqualifiers and constraints buried in the text:**
- Ages 13+, **students only** — companies and professional organizations excluded.
- Multi-submission to other hackathons is allowed, **but only this month**, and only if the
  other event also permits it.
- Prior work is allowed **but must be explicitly disclosed** (what was built before vs.
  during). Starting fresh on Sep 3 turns this from a liability into a clean narrative asset.

## 1b. Participant density read

**504 registered.** Projected **50–70 submissions** based on the 11.1% conversion observed in
2025 (885 → 98).

**What the average team looks like**, calibrated against the actual 2025 gallery: a solo
builder or pair of high schoolers shipping a web or React Native app that wraps a hosted LLM
API, with a 200–400 word Devpost writeup and a screen-recorded walkthrough. Many registrants
never submit at all.

**What the quality floor for *winning* looks like** — read directly off the 2025 winners:

| Project | Place | Stack | Depth |
|---|---|---|---|
| **DyslexicAssist** | 1st | React Native + Expo, Google Vision OCR, gpt-4o-mini, Node, TS | Multi-stage pipeline (OCR → cleanup → adaptive layout → TTS alignment → LLM summarization), RAG grounding, multi-armed bandit over layout settings, ~2,500-word writeup. **No live demo link.** |
| **Memora** | 2nd | Expo/RN, Python FastAPI on Railway, TensorFlow, Gemini, Supabase | CV + NLP integration, full-stack deploy, 14 screenshots, structured challenges/roadmap writeup. **No live demo link.** |
| **Eyelink** | 3rd | — | Sign-language / communication accessibility |

**The bar, stated plainly:** competent systems integration with a genuine multi-stage
pipeline, a real named user population, and a long, well-structured writeup. **Not**
algorithmic novelty. You can clear this bar in 10 days. Note especially that **two of three
winners shipped no live demo** — deployment is not where the points are.

## 1c. Prize structure — full parse

| Prize | Cash | Stacked |
|---|---|---|
| **1st** | $1,000 | $500 Claude credits + **YC final-round startup interview** + 2 AOPS coupons + XYZ domains + 1yr NordVPN/NordPass/Saily/Incogni |
| **2nd** | $500 | $250 Claude credits + 1 AOPS coupon + XYZ domains + 1yr bundle |
| **3rd** | $250 | $100 Claude credits + 1 AOPS coupon + XYZ domains + 1yr bundle |
| **Participation** | — | 700× Wolfram (full Wolfram Language + Knowledgebase, 5,000 API calls, 5,000 Cloud Credits, ~$830 value) + 350× XYZ domains |

**The single most valuable line item is the YC final-round interview**, and it is 1st place
only. If you are optimizing anything, optimize for 1st, not for "placing."

**⚠️ Critical finding — the standard special-prize play is UNAVAILABLE this year.**
There are **no "Best Use of X" category prizes** in 2026. I checked the prizes section and
the resources page. The resources page lists only **W3Schools, repl.it, Udemy, and YouTube** —
no sponsor APIs, no credits, no bonus categories. It says *"Please check back consistently
for more updates on resources!"*, so this may change, but as of today there is nothing to
stack.

**The one live possibility to monitor:** **Kinetik** is listed as a 2026 sponsor, and in 2025
Kinetik funded a separate **$1,000 "Future of Work"** category. If they repeat it, that is a
second $1,000 prize pool with far lower competition. **Watch the Devpost Updates tab and the
Discord.** Caveat: "Future of Work" does not naturally fit "Earth Forward," so it would
likely be a parallel category rather than a stack — don't distort your build for it
speculatively.

**Soft sponsor signal:** Claude credits appear at **all three** prize tiers and Anthropic is
the headline sponsor. This is not a scored category, but deep, non-trivial use of the Claude
API is a legitimate tiebreaker signal to the organizers. Use it where it genuinely fits.

## 1d. Submission requirements as hard design constraints

| Deliverable | What it requires | What it rules out | What it implicitly rewards |
|---|---|---|---|
| **Video ≤ 5 min** | Entire value legible in under 5 minutes | Anything needing long setup exposition; anything whose "wow" lives in the backend | Visual output. Front-loaded payoff. Volunteer judges reviewing dozens of videos will decide in the **first 45 seconds** |
| **Repo link (required)** | Code will be opened by professional software engineers | Single-file vibe-coded blob; a commit history that all lands in one 3-hour window on Sep 12 | Clean README with architecture, honest commit history spread across the window — this also directly feeds **Learning** and the prior-work disclosure rule |
| **Live link ("if applicable")** | — | Nothing | **This is soft.** Two of three 2025 winners had none. Massive de-risking: you do not need a bulletproof deploy. But shipping a working one when peers don't is a free **Completion** differentiator |
| **Prior-work disclosure** | State before/during split | — | Starting clean on Sep 3 gives you an unambiguous, honest story |
| **Devpost writeup** (de facto) | Not formally listed — but both known winners wrote ~2,500 structured words | — | **The single most underrated deliverable.** It is the only channel that can score the **Learning** criterion, which is 1/6 of the rubric and which no video can convey |

### FINAL CONSTRAINT LIST — every candidate below must satisfy all eight

- **C1.** Demoable end-to-end in ≤5 min, with the "wow" visible in the first 45 seconds.
- **C2.** No hardware, no proprietary data, no field deployment. Must run on a laptop against free/public data.
- **C3.** Must have a real visual interface. **Design is 1 of 6 criteria** — a CLI or notebook forfeits ~17% of the rubric outright.
- **C4.** Must have a defensible "this was technically hard" story for SWE judges (Technology: *"difficult… clever technique… many different components… make you go wow"*).
- **C5.** Must be anchored to a **specific named place/community**, not a global abstraction (Adherence: "fully vs. partially").
- **C6.** Must reach **Completion** in 10 days. "Does the hack work?" outranks scope every time.
- **C7.** Must generate a genuine "what I stretched into" narrative (Learning).
- **C8.** Repo must read like 10 days of real work.

## 1e. Technology deep read

There is **no mandated stack and no sponsor API** this year. That is freeing — it means zero
forced-integration risk, and you should pick the most mature tools available.

**Sponsor-adjacent tools worth real consideration:**

| Tool | Good at | Mediocre at | Strategic note |
|---|---|---|---|
| **Claude API** | Structured reasoning, tool use, long-context document analysis, agentic pipelines, generating explanations from structured data | Real-time low-latency vision loops | Headline sponsor; credits at every tier. Deep use is a soft signal to organizers |
| **Wolfram** (participation prize: full Language + Knowledgebase + 5,000 API calls) | Curated geographic/environmental/weather knowledgebase, unit-aware computation, symbolic math and optimization | Modern web UI | **Genuinely underused.** Every participant receives a license and almost none will touch it. Deep use is a real differentiator on Originality and Technology |

**Free environmental data — maturity and risk ratings:**

| Source | Maturity | Risk |
|---|---|---|
| Open-Meteo (weather/climate, no key) | Mature | **Low** |
| NASA POWER (solar/meteorological) | Mature | **Low** |
| OpenStreetMap / Overpass API | Mature | **Low** |
| USGS / Landsat surface temperature | Mature | Low–medium (data volume) |
| American Forests **Tree Equity Score** API | Mature, free | **Low** |
| US Census / ACS (demographics) | Mature | **Low** |
| EPA AirNow + PurpleAir | Mature | Low–medium (PurpleAir key required) |
| GBIF / iNaturalist / BirdNET (open model) | Mature | Low |
| Sentinel-2 via Copernicus / Planetary Computer | Mature | Medium (heavy pipeline) |
| **WattTime** | Mature | **HIGH — free tier is CAISO_NORTH only** |
| **Google Earth Engine** | Mature | **HIGH — requires approval; will not clear in 10 days** |

**Used superficially by most teams:** OpenAI/Gemini chat completion generating "sustainability
tips."
**Rewards deep integration:** geospatial pipelines, satellite/aerial imagery analysis, open
ecological datasets, optimization, and the Wolfram knowledgebase.

## 1f. Judge intelligence — MANDATORY RESEARCH

### The honest headline: the 2026 panel is not published, and "HackAlphaX Team" is a placeholder.

The Judges section lists only **"HackAlphaX Team."** But the event page simultaneously links
an open **Volunteer/Judging Form** (`forms.gle/U7gJNiyixNUwtr3n9`), meaning recruitment was
still in progress at the time of writing. I therefore researched the two prior years to
establish what that recruitment actually produces.

### Verified prior panels

**NextStep Hacks 2024 — 16 judges:**

| Judge | Role |
|---|---|
| Aditya Kirubakaran | Founder, HackAlphaX |
| Aman Gupta | Amazon |
| Sanjana Kandi | NVIDIA |
| Letian Xu | Google |
| Weining Qian | TikTok |
| Abdul Sajid Mohammed | Microsoft |
| Kaustubh Prabhakar | X/Twitter, Apple, Snap |

**NextStep Hacks 2025 — 20 judges:**

| Judge | Role | Domain they actually work in |
|---|---|---|
| **Nidhi Mahajan** | Director, Business Strategy & Program Operations @ **Visa** | Business strategy, program ops — not engineering |
| **Sanath Chilakala** | Director, **Data & AI** @ NTT Data | Production data/ML platforms |
| **Anand Upendrakumar Desai** | **AI Core Engineer** @ Microsoft | Applied ML engineering |
| **Parth Jain** | SDE @ **Netflix** | Backend/distributed systems |
| **Kelvin Ngoc Nguyen Le** | Staff Software Engineer @ Knoetic | Full-stack/platform |
| +15 more | Amazon, Walmart, Oracle, Bloomberg, **Tesla**, CVS | Mixed SWE / data |

**Organizing body (hackalphax.co)** — student-run, founded 2020, ~3,000 students reached over
six years. Leadership: **Aaditya Mittal** (Executive Director), **Krishnan Shankar**
(Operations & Technical Lead — Computer Engineering at UIUC, TJHSST alum, GitHub
`krishnans2006`), **Ashwin Kirubakaran** (Assistant Director), plus regional directors. The
org's own site carries no judging information; the student team runs operations while the
scoring panel is recruited externally.

### PANEL SYNTHESIS — what this panel actually rewards

**Dominant background:** mid-to-senior **software engineers and data/AI practitioners at
large US tech and enterprise companies.**

**The finding that should drive your entire strategy:** across two published panels and 36
judges, **I found zero judges with an environmental, climate, or sustainability title.** Not
one.

Five consequences, in order of importance:

1. **Your climate science will not be deeply audited.** Do not over-invest in scientific
   rigor the panel cannot evaluate. Invest in rigor that is *visible*.
2. **Engineering is where their expertise lives, and it is where they will actually
   discriminate.** "Technology" and "Completion" are the two criteria this panel can judge
   with genuine authority — and they will. Architecture, data pipelines, ML integration, and
   clean code carry disproportionate weight relative to environmental novelty.
3. **A real data/ML pipeline over real data beats an LLM wrapper decisively.** Sanath
   Chilakala (Director of Data & AI) and Anand Desai (AI Core Engineer at Microsoft) ship ML
   systems for a living. They can distinguish a genuine multi-stage pipeline from a prompt
   call in under 30 seconds, and the gap between those two is the gap between 3rd place and
   nothing.
4. **A business-strategy judge like Nidhi Mahajan rewards a crisp problem statement,
   quantified impact, and a coherent go-forward.** Put a real number on the problem in the
   first 30 seconds of the video.
5. **These are volunteers reviewing dozens of 5-minute videos, probably in one or two
   sittings.** Managing their cognitive load is a scoring strategy, not a courtesy. Front-load
   everything.

**⚠️ Confidence caveat, stated explicitly:** the 2026 panel is **not yet published.** The
above is inference from two consecutive years of the *same* recruiting mechanism (public
volunteer form → industry professionals), which makes it a high-confidence prior — but it is
a prior, not a fact. **Re-check the Judges tab before you submit.** If the panel shifts toward
environmental domain experts, the calculus in Phase 4 changes and you should re-weight toward
scientific defensibility.

---

# PHASE 2 — SOLUTION SPACE MAPPING

## 2a. Track selection decision

There are no formal tracks, so I scored the **five named theme sub-domains** as de facto
tracks. (Judge coverage scores are low across the board because, as established, no judge has
environmental domain expertise — the score reflects *adjacent technical legibility*.)

| Sub-domain | Judge coverage | Competition density *(lower density = higher score)* | Prize opportunity | Builder fit | Problem richness | **Total** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **Climate resilience / adaptation** | 3 | 4 | 4 | 5 | 5 | **21** |
| Conservation / biodiversity | 3 | 4 | 4 | 5 | 4 | **20** |
| Sustainable agriculture | 2 | 4 | 3 | 3 | 3 | **15** |
| Renewable energy | 3 | 4 | 4 | 4 | 4 | **19** |
| Waste reduction | 2 | **2** | 3 | 4 | 3 | **14** |

### ➤ This analysis recommends **CLIMATE RESILIENCE / ADAPTATION** because:

1. **It has the richest supply of free, high-resolution public geospatial data** — and
   geospatial data renders as a **map**, which is the most visually impressive thing you can
   put on screen in a 5-minute video (satisfies C1 hardest).
2. **It is the least-attacked sub-domain in student hackathons**, which skew overwhelmingly
   toward *mitigation* (carbon tracking, recycling) rather than *adaptation*.
3. **Its natural implementation shape — multi-source data fusion + geospatial analysis +
   a scored/optimized output — is precisely the engineering this Data/AI-heavy panel
   recognizes and rewards** on the Technology criterion.
4. **It satisfies C5 automatically**, because adaptation is inherently local. You cannot build
   an adaptation tool without naming a place.

**Waste reduction scores lowest and should be actively avoided** — it is where both default
solutions live.

All subsequent phases operate within climate resilience/adaptation.

## 2b. Default solution mapping — DO NOT BUILD THESE

For "Earth Forward" there are **two** dominant defaults, not one. Named as patterns:

> **DEFAULT #1 — "The AI carbon footprint tracker."**
> A Next.js/React web app with a form or receipt/photo upload; an LLM call that estimates CO₂e
> for the item or activity; a dashboard with a bar chart and a running total; gamified
> badges, streaks, and a friends leaderboard. Often bolted to a "green tips" chatbot.
> **Estimated 25–40% of submissions will be a variant of this.**

> **DEFAULT #2 — "Point your camera at the trash."**
> A mobile or web app using a pretrained image classifier or a multimodal LLM that identifies
> an object from a photo and says which bin it belongs in, plus a points/streak system and a
> "you saved X kg of CO₂" counter.
> **Estimated another 15–25%.**

**Both fail identically against this specific rubric:**
- **Originality** — the criterion literally asks *"Has this project been done before at
  hackathons in the past?"* The answer is yes, hundreds of times, and volunteer judges who
  have judged multiple hackathons will recognize it on sight.
- **Technology** — a form plus an API call is not "technically difficult" to a Netflix or
  Microsoft engineer.
- **Adherence (fully vs. partially)** — *estimating* environmental impact is not an
  environmental *intervention*. It reads as partial implementation.

**Evidence caveat, stated honestly:** I could not retrieve hard Devpost project counts —
Devpost's search page is JavaScript-rendered and returned empty content to both `curl` (403,
WAF-blocked) and WebFetch. **The percentages above are calibrated estimates, not
measurements.** What *does* support the structural claim is the 2025 gallery for this same
event, which shows exactly this clustering behavior against that year's theme: **Voxa AI,
Speak-EZ, HearMeOut,** and **Resonate** all converged on near-identical speech/sign-language
assistance concepts. This event reliably produces heavy clustering on the obvious reading of
the theme.

**Neither default may appear in the final three. They do not.**

## 2c. Existing solution landscape — evidence before any gap claim

| Solution | Genuine steelman | What it does not solve |
|---|---|---|
| **First Street Foundation / Risk Factor** (riskfactor.com) | Peer-reviewed property-level flood/fire/heat/wind models, national coverage, free consumer lookup, integrated into Zillow and Redfin. Genuinely excellent science. | Gives you a **score and stops.** No guidance on what to do, what it costs, or what you qualify for. **Diagnosis without prescription.** |
| **FEMA National Risk Index** | Official, free, comprehensive across 18 hazards, tract-level. | County/tract resolution is useless at household scale; it is a planner's tool with a planner's UI. |
| **NOAA HeatRisk / CMRA** | Authoritative federal data, free, well-maintained. | Built for municipal planners. No personalization, no action layer. |
| **Tree Equity Score** (American Forests) | Excellent and genuinely well-designed: block-group canopy + heat + demographics, free API, real methodology. | It is an **advocacy and analysis map.** It shows you the disparity. It does **not** plan an intervention or tell a specific neighborhood where to put the next 40 trees for maximum cooling per dollar. |
| Local government heat/flood plans | Locally specific, often well-researched. | Distributed as **PDFs.** Not queryable, not actionable, not personalized. |

**The persistent gap, stated precisely:** *the last mile from a risk score to specific,
costed, prioritized action for a non-expert at household or neighborhood scale.*

**Evidence that this gap is real and not my assertion:** the tree-equity literature documents
that the disparity **persists** — 62 million fewer trees in low-income blocks, low-income
blocks up to **4.0 °C hotter** in parts of the Northeast, 92% of US cities showing more
residents of color in their hottest neighborhoods — *despite the data being public, mapped,
and freely available for years.* A disparity that survives full data transparency is the
signature of a problem that was never a data-availability problem. **It is an
action-planning problem.**

---

# PHASE 3 — PROBLEM IDENTIFICATION

## Scoring note — an honest methodology substitution

Dimension **F (Special Prize Alignment)** is meaningless as written this year, because **there
are no special category prizes** (see 1c). Scoring every problem identically on F would flatten
the arithmetic and hide real differences. I have therefore **redefined F for this event** as:

> **F = Sponsor-signal alignment** — does this problem naturally permit *deep, non-forced* use
> of **Claude** (headline sponsor, credits at all three tiers) and/or **Wolfram** (universal
> participation license, 5,000 API calls, and almost universally ignored)?

This substitution is disclosed rather than silent, and applied uniformly.

**Dimensions:** A = Pain Evidence · B = Solution Gap · C = Hackathon Fit · D = Judge Resonance
· E = Feasibility (LLM-augmented) · F = Sponsor-signal alignment. Each 1–5, total /30.

| # | Problem (≤2 sentences) | A | B | C | D | E | F | **Total** |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **P1** | **Neighborhood heat-mitigation planning at block scale.** Community groups and under-resourced city sustainability offices know which blocks are hot but have no way to decide where a limited budget of trees, shade structures, or cool roofs buys the most degrees per dollar. Tree Equity Score maps the disparity; nothing optimizes the intervention. | 5 | 4 | 5 | 4 | 5 | 4 | **27** |
| **P4** | **Rooftop solar silent underperformance.** Homeowners with solar lose 10–20% of annual generation to faults, soiling, and creeping shade they never detect, because inverter apps show raw production with no expected-vs-actual attribution. | 4 | 4 | 4 | 4 | 4 | 3 | **23** |
| **P9** | **Low-cost air sensor calibration for community science.** 30,000+ PurpleAir sensors feed community air-quality decisions, but raw readings carry large humidity-driven bias and the EPA's national correction is documented as materially worse in humid regions. | 4 | 4 | 4 | 4 | 4 | 3 | **23** |
| P2 | **Household wildfire home-hardening triage.** WUI homeowners know they're at risk but not which of ~30 possible mitigations to do first with $2,000; Risk Factor gives a score, Firewise gives a PDF checklist. | 4 | 4 | 4 | 3 | 4 | 3 | 22 |
| P3 | **Recycling rules fragmentation.** ~20,000 distinct US municipal programs mean a nationally "recyclable" label is locally wrong; two-thirds of consumers report confusion after reading labels. | 5 | 3 | 4 | 2 | 5 | 3 | 22 |
| P6 | **Bioacoustic conservation review bottleneck.** Passive acoustic monitoring generates thousands of hours of audio that cannot be manually reviewed, limiting practical ecological application. | 4 | 3 | 4 | 4 | 4 | 3 | 22 |
| P7 | **Household food waste.** EPA (Apr 2025) puts consumer food waste at $728/capita — $2,913 for a household of four — nearly double the decade-old $1,500 figure. | 5 | 3 | 3 | 2 | 5 | 3 | 21 |
| P8 | **Illegal dumping hotspot prediction.** Houston spends $11.5M/yr and LA $36M on cleanup at $230–600/ton, while 311 systems remain reactive. | 4 | 3 | 3 | 3 | 4 | 3 | 20 |
| P5 | **Grid-carbon-aware household load shifting.** Shifting flexible loads to low-carbon hours is promoted as a lever, but the Electricity Maps literature argues marginal signals may *not* actually reduce footprint. | 3 | 3 | 3 | 4 | 3 | 3 | 19 |
| P10 | **Smallholder irrigation scheduling.** UNL CropWatch found irrigators overwater in wet years and sometimes underwater in dry ones; sensor adoption remains low. | 3 | 3 | 3 | 2 | 3 | 3 | 17 |

### ➤ TOP 3 BY ARITHMETIC ONLY

1. **P1 — Neighborhood heat-mitigation planning (27)**
2. **P4 — Rooftop solar silent underperformance (23)** *(tied)*
3. **P9 — Low-cost air sensor calibration (23)** *(tied)*

P4 and P9 tie exactly at 23. Both advance. Note that **P3 (recycling) scores 22 and is
excluded** — which is correct, because it collides directly with Default #2 and would be
scored down hard on Originality in practice.

---

# PHASE 4 — TOP 3 DEEP DIVES

---

## ① COOLBLOCK — *"Where should the next 40 trees go?"*

### THE PROBLEM

A neighborhood association or a two-person city sustainability office has a real but small
budget — say $50,000 — for heat mitigation, and no defensible way to spend it. They can see
on a public map that their blocks are hot; what they cannot answer is **which specific
parcels, if planted or shaded, deliver the most cooling to the most heat-vulnerable people
per dollar.** The moment of friction is a planning meeting where someone asks "so where do
they actually go?" and the answer is a guess, a squeaky-wheel request, or whichever block the
most vocal homeowner lives on.

**Measurable cost:** low-income blocks in some Northeast urbanized areas run **4.0 °C hotter**
with **30% less tree cover**; there are an estimated **62 million fewer trees** in low-income
blocks than wealthy ones; **92% of US cities** have more residents of color and higher poverty
rates in their hottest neighborhoods.

### EVIDENCE OF REAL PAIN

1. **PLOS ONE** — *"The tree cover and temperature disparity in US urbanized areas:
   Quantifying the association with income across 5,723 communities"* (doi:10.1371/journal.pone.0249715).
   The 4.0 °C / 30%-less-canopy figures for Northeast low-income blocks.
2. **Nature Communications** — *"Trees halve urban heat island effect globally but unequal
   benefits only modestly mitigate climate-change warming"* (s41467-026-71825-x). Documents
   that cooling benefits accrue disproportionately to **higher incomes and suburbs**. Dataset
   mirrored on Dryad (doi:10.5061/dryad.905qfttz0).
3. **npj Urban Sustainability** — *"Increasing tree canopy lowers urban air temperature by up
   to 1.5 °C in heat-prone areas"* (s42949-025-00277-x). Establishes the intervention→degrees
   relationship your optimizer needs.
4. **Scientific Reports** — *"Street trees provide an opportunity to mitigate urban heat and
   reduce risk of high heat exposure"* (s41598-024-51921-y).
5. **American Forests, Tree Equity Score** — *Urban Heat Equity* data short
   (treeequityscore.org/stories/urban-heat-equity), plus the 62-million-tree gap and the
   92%-of-cities finding via Journalist's Resource and Courthouse News coverage.

**Five sources, all findable, all peer-reviewed or institutional. This is the strongest
evidence base in the pool.**

### EXISTING SOLUTIONS AND WHY THEY FAIL

- **Tree Equity Score (American Forests).** *Steelman:* genuinely excellent — block-group
  canopy, heat, health, and demographic data, a free API, transparent methodology, national
  coverage, and a clean UI. It is the best thing in this space and it is free. *Why the gap
  persists:* it is a **scoring and advocacy instrument.** It tells you a block group scores 62
  instead of 100. It does not ingest your budget, does not know where the plantable space
  physically is, does not rank candidate parcels, and does not produce a plan. The disparity
  it maps has persisted for years *while the map was public* — which is exactly the evidence
  that mapping was never the bottleneck.
- **Municipal urban forest master plans.** *Steelman:* often genuinely rigorous, written by
  real arborists, with canopy targets. *Why the gap persists:* they are **PDFs on a
  city website**, updated every 10 years, at city-wide resolution, and unusable by the
  neighborhood group holding the actual $50,000.
- **i-Tree (USDA Forest Service).** *Steelman:* the scientific gold standard for quantifying
  tree benefits, free, and trusted by professionals. *Why the gap persists:* it is a suite of
  expert tools that **quantifies benefits of trees you already have or specify.** It is a
  calculator, not a siting optimizer, and its UX assumes a trained urban forester.

### PROPOSED SOLUTION DIRECTION

A **block-scale heat-mitigation siting optimizer.** The user drops a pin on a neighborhood and
enters a budget. The system:

1. Pulls **Landsat/Sentinel land-surface temperature** for the area and builds a heat surface.
2. Pulls **OpenStreetMap/Overpass** building footprints, road segments, and parcels, plus
   **Census/ACS** demographics and **Tree Equity Score** canopy data.
3. Segments aerial imagery to identify **actually plantable space** — the step that separates
   this from every existing map.
4. Runs a **constrained optimization** over candidate sites: maximize (cooling effect ×
   heat-vulnerable population reached) subject to budget, using the degrees-per-canopy-increment
   relationships from the npj/Nature literature.
5. Renders the chosen sites on a map with a **before/after modeled heat surface**, a per-site
   cost, and a Claude-generated **plain-language justification memo** the group can actually
   take to a city council meeting.

**The core insight:** *Everyone has built the map. Nobody has built the plan.* The gap is not
"which blocks are hot" — that has been public for a decade — it is "given $50,000 and this
specific geography, here are the 40 parcels, ranked, with the modeled degrees each one buys."

**The 3-minute demo:** pin drop on a named, real, hot neighborhood → heat surface renders →
budget slider → optimizer runs visibly → 40 pins appear ranked → before/after heat surface
toggles → the justification memo generates. **The map is on screen inside 20 seconds.**

**Technology mapping (specific capabilities, not logos):**
- **Claude API** — not for chat. For **structured-data-to-narrative generation**: turning the
  optimizer's ranked output into a council-ready memo with citations, and for tool-use over
  the parcel dataset. This is a legitimate deep use, not a wrapper.
- **Wolfram** — genuinely fits here for the **unit-aware geospatial computation and the
  optimization step**, plus its curated geographic knowledgebase. Almost no other team will
  touch Wolfram at all.

### SPECIAL PRIZE STACK OPPORTUNITY

**None available — and I am not going to invent one.** There are no "Best Use of X" categories
in 2026. What this project does have is the strongest available **sponsor-signal** position:
deep, non-forced use of both Claude and Wolfram, which is the closest thing to a stack that
exists this year. If **Kinetik** announces a category mid-event, reassess then — but do not
distort the build for it.

### SUBMISSION REQUIREMENT FIT

| Constraint | Fit |
|---|---|
| C1 — 5-min demo, wow in 45s | ✅ **Strongest in the pool.** A map with a heat surface is instantly legible |
| C2 — free/public data, laptop-runnable | ✅ Landsat, OSM, Census, Tree Equity Score — all free, no approval needed |
| C3 — real visual interface | ✅ Map-first UI; Design criterion is a strength, not a tax |
| C4 — technically hard story | ✅ Imagery segmentation + multi-source geospatial fusion + constrained optimization = four genuinely different components |
| C5 — specific named place | ✅ **Automatic.** You will name a real neighborhood |
| C6 — completable in 10 days | ⚠️ Requires disciplined scoping — see risks |
| C7 — learning narrative | ✅ Geospatial analysis and optimization are almost certainly new territory |
| C8 — repo reads like real work | ✅ Naturally decomposes into distinct, committable modules |

### JUDGING CRITERION ALIGNMENT

- **Originality** — scores high because the pool is saturated with *measurement* tools
  (trackers, classifiers) and this is a *decision* tool. To a judge who has seen ten carbon
  trackers that evening, an optimizer is categorically different.
- **Adherence to Track (fully)** — scores high because it is a concrete environmental
  intervention anchored to a named community, hitting the theme statement's explicit
  "collaborate with local organizations… real-world needs" language rather than a global
  abstraction.
- **Completion** — scores well *if scoped correctly*: one named neighborhood, working
  end-to-end, beats five cities half-working.
- **Learning** — scores high; geospatial pipelines and constrained optimization are a genuine
  stretch and produce an honest, specific writeup.
- **Design** — map-centric UI with a before/after toggle is inherently demoable and gives the
  Design criterion something real to reward.
- **Technology** — scores highest here: *"did it use many different components?"* — imagery
  segmentation, raster analysis, demographic joins, optimization, and LLM report generation
  are five distinct components. *"Did the technology make you go wow?"* — a modeled before/after
  heat surface does.

### JUDGE RESONANCE ANALYSIS

- **Sanath Chilakala (Director, Data & AI @ NTT Data)** — this is a **multi-source data fusion
  pipeline**, which is literally his job. He will recognize the difficulty of joining raster
  temperature data to vector parcels to block-group demographics, because that class of join
  is where real data projects die. Frame it in that language: "the hard part was the join, not
  the model."
- **Anand Upendrakumar Desai (AI Core Engineer @ Microsoft)** — will evaluate the imagery
  segmentation and the optimizer on their merits. Show him the failure modes you handled.
- **Nidhi Mahajan (Director, Business Strategy & Program Ops @ Visa)** — will respond to
  *"$50,000 budget, 40 ranked parcels, modeled degrees per dollar."* That is a resource
  allocation problem stated in her native language. Lead the video with the cost figure.
- **The Tesla / Amazon / Oracle engineering bloc** — respond to visible systems complexity and
  a clean architecture diagram.

**Framing that makes them lean forward:** *"The data has been public for ten years and the
disparity hasn't moved. That's not a data problem — it's an allocation problem. So I built the
allocator."*

### HONEST RISK FLAGS

- **Assumption that could be wrong:** that the degrees-per-canopy-increment relationships in
  the literature are transferable to block scale in your chosen city. They are derived at
  coarser resolution. **Validate in the first 3 days** by checking whether your modeled heat
  surface reproduces known hot spots in the real neighborhood; if it doesn't, downgrade the
  claim from "predicted cooling" to "prioritization score" and say so honestly in the writeup.
  Judges reward that honesty under **Learning**; overclaiming is what gets caught.
- **External dependency:** Tree Equity Score API availability. Mitigate by caching the data
  for your target neighborhood locally on day 1.
- **Scope risk (the real one):** this is the most ambitious of the three. The failure mode is
  a half-built pipeline on Sep 13.

### INTEGRATION RISK FLAGS

- **Where LLM-generated code is least reliable:** **geospatial coordinate handling.**
  Projections, CRS transforms, and raster–vector alignment are where frontier models
  confidently produce subtly wrong code. Expect to debug CRS mismatches by hand. Budget real
  time for it. Everything else here is standard.
- **Poorly-suited APIs:** **avoid Google Earth Engine entirely** — it requires approval you
  will not obtain in 10 days. Use Landsat via a STAC catalog or precomputed LST products.
- **Most likely demo failure:** a live raster fetch timing out mid-video. **De-risk by
  precomputing and caching all raster data for the demo neighborhood**, so the demo runs
  entirely against local files. Record the video against the cached path.

### COMPETITIVE POSITIONING

Other teams will not build this because it requires stepping outside the app-with-an-LLM-call
comfort zone into geospatial data engineering — a domain with a genuinely steep first day and
no tutorial-shaped path. The **non-obvious angle** is the reframe from *measurement to
allocation*: in a field of tools that tell you how bad things are, this is the only one that
tells you what to do. The **real barrier to replication** is the plantable-space segmentation
plus the optimizer formulation; a team could clone the map in a day, but the ranked, costed
output is where the actual work lives.

---

## ② SOLARGHOST — *"Your panels have been losing money for four months."*

### THE PROBLEM

A homeowner with rooftop solar checks their inverter app, sees a production number, and has
no idea whether it is a *good* number. Meanwhile a tree that was harmless at installation has
grown into the array's peak-production window, or a soiling layer has built up, and they are
silently losing generation. The moment of friction is an electricity bill that is higher than
expected and a monitoring app that offers no explanation.

**Measurable cost:** unmonitored systems lose an estimated **10–20% of annual generation** to
undetected faults and soiling; a **single bird dropping** on one cell of a string-inverter
system can cost **5–25% of that string's production**.

### EVIDENCE OF REAL PAIN

1. **Team Solar Works** — *"Silent Losses: How to Detect and Correct Hidden Solar System
   Underperformance."* Source of the 10–20% annual-generation loss figure for unmonitored
   systems.
2. **US Power Solar** — *"How to Monitor Solar Panel Performance: 7 Warning Signs."*
   Documents the "black box" homeowner experience and the single-bird-dropping / 5–25%
   string-loss mechanism.
3. **SAMS MD** — *"How to Identify an Underperforming Solar System."* Documents shading drift
   over time: trees grow, adjacent structures get built, and an array that was unshaded at
   install is shaded five years later.
4. **US Patent 10,998,853** — *"Internet of things-enabled solar photovoltaic health
   monitoring and advising."* Patent activity in this exact space is direct evidence that the
   problem is commercially recognized and unsolved at the consumer tier.
5. **US Patent 12,017,256** — *"Photovoltaic soil monitoring system with automated clean
   referencing system."* Same signal, specifically for soiling.

**Honest note on evidence quality:** three of five sources are solar-industry vendor blogs
rather than peer-reviewed work. They are consistent with each other and with the patent
record, but they have a commercial interest in the problem existing. **This is weaker
evidence than P1's peer-reviewed base**, and it is why P4 scored 4 on Pain Evidence rather
than 5.

### EXISTING SOLUTIONS AND WHY THEY FAIL

- **Inverter manufacturer apps (Enphase, SolarEdge, Tesla).** *Steelman:* genuinely good at
  what they do — real-time production, often per-panel telemetry with microinverters, clean
  mobile UX, already installed on every relevant homeowner's phone. *Why the gap persists:*
  they show **actual production with no expected baseline.** 40 kWh means nothing without
  "you should have made 52 today given this weather, this array geometry, and this season."
  Attribution — *why* the gap exists — is entirely absent.
- **Professional O&M monitoring platforms (Also Energy, Raptor Maps).** *Steelman:* genuinely
  solve this, with physics-based expected-generation models and fault classification.
  *Why the gap persists:* they are **commercial platforms priced and designed for utility and
  commercial fleet operators.** A residential homeowner cannot buy or operate one.
- **Manual PVWatts comparison.** *Steelman:* free, NREL-backed, and technically the right
  physics. *Why the gap persists:* requires the homeowner to know their array's tilt, azimuth,
  derate factors, and to manually cross-reference monthly. Effectively nobody does this.

### PROPOSED SOLUTION DIRECTION

An **expected-vs-actual attribution engine** for residential solar. Given an array's location,
tilt, azimuth, and capacity, the system builds a physics-based expected-generation curve from
**NASA POWER / PVWatts irradiance and weather data**, compares it against the homeowner's
actual production, and — the key step — **classifies the residual** into probable causes:
soiling (gradual decay recovering after rain), shading (time-of-day-specific, seasonally
drifting), inverter fault (step change), or weather (already accounted for).

**The core insight:** *The signal isn't the production number — it's the shape of the gap over
time.* Soiling, shading, and hardware faults each leave a distinct temporal fingerprint in the
residual, and separating them is what turns "you produced 40 kWh" into "a tree has been
shading your east string since June."

**The 3-minute demo:** load a real array's production history → expected curve overlays →
the residual is highlighted → the classifier labels three distinct events on the timeline →
click one → "shading, east string, onset mid-June, estimated 340 kWh and $61 lost to date."

**Technology mapping:** **Claude API** for generating the diagnostic explanation and the
recommended action from the classifier's structured output. Physics modeling from PVWatts /
NASA POWER (both mature, free, no approval).

### SPECIAL PRIZE STACK OPPORTUNITY

**None available.** Sponsor-signal alignment is moderate — Claude fits naturally for
explanation generation, but there is no compelling Wolfram angle here, which is why F scored 3
rather than 4.

### SUBMISSION REQUIREMENT FIT

Strong on C1 (a time-series chart with a labeled residual is legible fast), C2, C3, C4, C6,
C7, C8. **Weakest on C5** — "homeowners with solar" is a population, not a place. Mitigate by
anchoring to a specific named city's solar stock and using that city's real weather data.

### JUDGING CRITERION ALIGNMENT

- **Originality** — high; nobody at a student hackathon builds attribution engines.
- **Adherence (fully)** — good but not maximal; recovering lost renewable generation is
  squarely on-theme, though less visibly "community" than P1.
- **Completion** — **strongest of the three.** The scope is naturally bounded and the pipeline
  is short.
- **Learning** — high; time-series decomposition and physics modeling are a real stretch.
- **Design** — good, though a chart is less arresting than a map.
- **Technology** — high: physics simulation + time-series anomaly detection + classification
  is a genuinely respectable stack, and *"clever technique"* describes residual decomposition
  well.

### JUDGE RESONANCE ANALYSIS

- **Sanath Chilakala (Data & AI, NTT Data)** and **Anand Desai (AI Core Engineer, Microsoft)**
  — **this is the strongest pure-ML resonance of the three.** Expected-vs-actual residual
  decomposition with fault classification is a canonical industrial ML pattern. They will
  immediately recognize it as real work rather than a wrapper.
- **The Tesla judge (2025 panel)** — direct domain adjacency to solar and energy hardware.
  If a comparable judge returns in 2026, this is your highest-leverage single connection.
- **Parth Jain (Netflix)** — time-series anomaly detection is core observability engineering.

**Framing:** *"Every inverter app shows you production. None of them show you the counterfactual.
I built the counterfactual, then classified the gap."*

### HONEST RISK FLAGS

- **The load-bearing assumption:** that the three failure modes are actually separable in the
  residual with the data resolution available. **Validate in the first 3 days** on a real
  public production dataset. If they aren't cleanly separable, fall back to
  detection-plus-ranked-hypotheses rather than confident classification — and say so.
- **Data dependency:** you need real residential production time series. Public datasets
  (NREL, PVOutput) exist, but confirm access on day 1 before committing.

### INTEGRATION RISK FLAGS

- **Where LLM code is least reliable:** **solar geometry and timezone handling.** Solar
  position calculations, timezone/DST alignment between weather data and production data, and
  irradiance-to-AC-power derating are all places where generated code is confidently wrong.
  Use the `pvlib` library rather than hand-rolled math, and verify against a known reference day.
- **Most likely demo failure:** the classifier labels a weather event as a fault on camera.
  **De-risk** by curating the demo dataset to a window with verified ground-truth events, and
  keeping a cached run.

### COMPETITIVE POSITIONING

Other teams won't build this because it requires physics modeling before any ML, which has no
tutorial path and no obvious LLM shortcut. The **non-obvious angle** is that the product is
the *residual*, not the prediction. The **barrier to replication** is getting the expected-
generation baseline accurate enough that the residual is meaningful — a bad baseline makes the
entire classifier noise, and that calibration is genuinely hard-won.

---

## ③ TRUEAIR — *"Your neighborhood's air data is wrong in a way nobody told you."*

### THE PROBLEM

Community groups and residents in environmental-justice neighborhoods increasingly rely on
low-cost **PurpleAir** sensors to document air quality — often as the *only* monitoring their
area has. But raw readings carry substantial humidity-driven bias, and the EPA's national
correction equation is documented as materially less accurate in humid regions. The friction
moment is a community group bringing sensor data to a regulator or a council and having its
accuracy challenged.

**Measurable cost:** **30,000+ networked PurpleAir sensors** as of April 2022 feed real-time
public air-quality information; applying region-appropriate correction reduces error metrics
by **16–23%** versus the EPA's national model in humid conditions.

### EVIDENCE OF REAL PAIN

1. **Atmospheric Measurement Techniques (Copernicus), vol. 17, p. 6735 (2024)** —
   *"Calibration of PurpleAir low-cost particulate matter sensors: model development for air
   quality under high relative humidity conditions."* Establishes RH as the primary error
   source and reports the **16–23% error reduction** over the EPA Barkjohn model. Also in
   PubMed (40078349) and PMC11900072.
2. **Atmospheric Measurement Techniques, vol. 16, p. 1311 (2023)** — *"An evaluation of the
   U.S. EPA's correction equation for PurpleAir sensor data in smoke, dust, and wintertime
   urban pollution events."* Independent evaluation of where the national correction breaks
   down.
3. **PMC11859157** — *"A Systematic Study of Popular Software Packages and AI/ML Models for
   Calibrating In Situ Air Quality Data: An Example with Purple Air Sensors."* Direct
   precedent that ML calibration is a live, active research approach.
4. **PMC10329730** — *"Investigating Use of Low-Cost Sensors to Increase Accuracy and Equity
   of Real-Time Air Quality Information."* Frames this explicitly as an **equity** problem.
5. **Data in Brief / ScienceDirect (S2352340922002190)** — PurpleAir calibration and
   inter-calibration dataset from Beirut, Lebanon; a usable public reference dataset.

**Five peer-reviewed sources. Evidence quality is second only to P1, and the gap here is
unusually crisply documented — the EPA itself published the correction, and the literature
quantifies exactly where it fails.**

### EXISTING SOLUTIONS AND WHY THEY FAIL

- **EPA AirNow Fire and Smoke Map (with the Barkjohn correction).** *Steelman:* a real
  achievement — the EPA built a national correction and integrated corrected PurpleAir data
  into AirNow, dramatically improving PM2.5 spatial coverage nationwide. Free and
  authoritative. *Why the gap persists:* the model was developed with **few sites in the
  southeastern US, the most humid region of the country**, and independent evaluation shows
  degraded performance in humid, smoke, dust, and wintertime conditions. A single national
  equation cannot be locally optimal everywhere.
- **PurpleAir's own map with the built-in conversion options.** *Steelman:* free, real-time,
  dense, and it does offer conversion factors. *Why the gap persists:* it offers the user a
  dropdown of conversion options with **no guidance on which is right for their conditions**,
  which pushes a scientific judgment onto a resident.
- **Regulatory reference monitors.** *Steelman:* the actual ground truth, rigorously
  maintained. *Why the gap persists:* they are **sparse** — which is the entire reason
  community sensor networks exist.

### PROPOSED SOLUTION DIRECTION

A **locally-calibrated community air quality service.** For a chosen region, the system
automatically pairs nearby PurpleAir sensors with the closest regulatory reference monitor,
**trains a local correction model** using RH and temperature as predictors, quantifies its
improvement over the EPA national equation on held-out data, and republishes the corrected
readings with **honest uncertainty bounds** — plus a generated methodology note a community
group can hand to a regulator.

**The core insight:** *The correction should be learned locally, not applied nationally* — and
the community's own sensor network plus the nearest reference monitor already contain enough
signal to learn it. The output is not just better numbers; it is **defensible** numbers.

**The 3-minute demo:** map of a real region's sensors → toggle raw / EPA-corrected /
locally-corrected against reference-monitor ground truth → the error metric drops visibly →
the methodology note generates.

**Technology mapping:** **Claude API** for generating the methodology note from model
diagnostics. PurpleAir + EPA AirNow APIs (both free) for data.

### SPECIAL PRIZE STACK OPPORTUNITY

**None available.** Sponsor-signal alignment is moderate (Claude fits for the methodology
note; no natural Wolfram angle), hence F = 3.

### SUBMISSION REQUIREMENT FIT

Good on C2, C3, C6, C7, C8. **Strong on C4** — a validated, quantified accuracy improvement is
unusually concrete. **C1 is the weak point:** "our regression has lower RMSE" is the hardest
of the three to make visually thrilling in 45 seconds. Mitigate by leading with the *map*
recoloring as the correction is applied, not with the error metric. **C5 is satisfiable** by
choosing a specific named environmental-justice neighborhood.

### JUDGING CRITERION ALIGNMENT

- **Originality** — high; no student hackathon project critiques and improves an EPA model.
- **Adherence (fully)** — good; environmental monitoring with an explicit equity framing.
- **Completion** — strong; the scope is naturally bounded and the pipeline is short.
- **Learning** — **highest of the three.** Reading atmospheric science papers and
  reimplementing a calibration model is an unusually credible stretch narrative, and the
  Learning criterion has no other easy way to be earned.
- **Design** — adequate; a map plus diagnostics, but less inherently striking than P1.
- **Technology** — high on *"difficult"* and *"clever technique"*; somewhat lower on
  *"many different components"* than P1.

### JUDGE RESONANCE ANALYSIS

- **Sanath Chilakala (Data & AI, NTT Data)** and **Anand Desai (Microsoft)** — will
  immediately appreciate a **held-out validation against a real baseline with a quantified
  improvement.** This is the one project of the three whose core claim is *empirically
  verifiable on screen*, which is rare in a hackathon and disproportionately persuasive to
  practitioners who spend their lives distrusting unvalidated models.
- **Nidhi Mahajan (Visa, Business Strategy)** — responds to the equity framing and the
  "defensible in front of a regulator" outcome.

**Framing:** *"The EPA published one equation for the whole country. The literature says it's
16–23% worse where it's humid. So I learned the local one, and here's the held-out validation."*

### HONEST RISK FLAGS

- **The load-bearing assumption:** that sufficient co-located PurpleAir + regulatory reference
  monitor pairs exist in your chosen region with enough overlapping history to train on.
  **Validate this on day 1 — before anything else.** If the pairs don't exist, the project
  has no ground truth and does not work. This is the single hardest dependency in the pool.
- **Secondary risk:** you may reproduce the published result rather than improve on it. That
  is still a defensible outcome if framed as replication-plus-localization, but be honest
  about it in the writeup.

### INTEGRATION RISK FLAGS

- **Where LLM code is least reliable:** **the sensor–monitor spatial/temporal join** —
  matching sensors to reference monitors within a radius, aligning timestamps across
  differing reporting intervals, and handling missing data. This is exactly the kind of
  fiddly data-alignment work where generated code silently misaligns and produces plausible
  but wrong results. Verify the join by hand on a small sample.
- **API risk:** PurpleAir now requires an API key with usage limits. **Request it on day 1**
  and cache aggressively.
- **Most likely demo failure:** a live API call failing or rate-limiting mid-video. **De-risk
  by snapshotting the full dataset locally** and demoing entirely offline.

### COMPETITIVE POSITIONING

Other teams won't build this because it requires reading atmospheric science literature before
writing code — a genuine barrier when the alternative is an afternoon with an LLM API. The
**non-obvious angle** is critiquing and locally improving a *government* model, which reframes
the project from "I made an app" to "I found a documented deficiency in federal methodology
and addressed it." The **barrier to replication** is the validation discipline: anyone can fit
a regression, but establishing a defensible held-out comparison against the EPA baseline is
where the credibility — and the work — actually lives.

---

# PHASE 5 — FINAL RECOMMENDATION

## ➤ Build **COOLBLOCK** (P1 — neighborhood heat-mitigation siting optimizer).

It wins over SolarGhost and TrueAir on the two things that actually decide this event. First,
the demo: a map with a modeled before/after heat surface is legible in fifteen seconds to a
volunteer judge on their ninth video of the evening, whereas SolarGhost's residual chart and
TrueAir's error metric both require the judge to *understand* something before they can be
impressed — and at five minutes with no domain expertise on the panel, comprehension is the
scarcest resource in the room. Second, it is the only one of the three that satisfies the
Adherence criterion's "fully vs. partially" test automatically, because you will name a real
neighborhood and a real budget, which is exactly what the theme statement's "collaborate with
local organizations… real-world needs" language is fishing for. It is also built precisely for
this panel: **Sanath Chilakala** (Director of Data & AI at NTT Data) and **Anand Desai** (AI
Core Engineer at Microsoft) will recognize a genuine multi-source raster-to-vector-to-demographic
fusion as real engineering rather than a wrapper, while **Nidhi Mahajan** (Business Strategy at
Visa) hears "$50,000, 40 ranked parcels, degrees per dollar" as a resource-allocation problem
stated in her own language — and it clears the Technology criterion's explicit "many different
components" test with five distinct ones. Realistically it competes for **1st place and the YC
interview**, and while there are no special category prizes to stack this year, it holds the
best sponsor-signal position available through non-forced deep use of both Claude and the
almost-universally-ignored Wolfram license every participant already receives. The single
biggest risk is **scope** — it is the most ambitious of the three and the failure mode is a
half-built pipeline on Sep 13 — and you manage it by fixing the scope to **one named
neighborhood, end to end**, on day one and refusing to generalize, because Completion is a
scored criterion and a working single-neighborhood tool beats a broken multi-city one every
time.

**In the first 72 hours, you must:**

1. **Pick the neighborhood and lock it. Today.** One city, one district, named. Never expand it.
2. **Cache every data source locally** — Landsat/Sentinel LST, OSM footprints, Census/ACS,
   Tree Equity Score — for that neighborhood only. After day 3 the demo should never touch a
   live API.
3. **Validate the heat surface against reality.** Does your modeled surface reproduce hot
   spots the city already knows about? If not, downgrade the claim from "predicted cooling" to
   "prioritization score" and say so plainly in the writeup — the Learning criterion rewards
   that honesty and overclaiming is what gets caught by engineers.
4. **Resolve the CRS/projection alignment by hand.** This is where LLM-generated geospatial
   code fails silently, and it blocks everything downstream. Do it before building any UI.
5. **Start the Devpost writeup on day 3, not day 10.** It is the only channel that can score
   the Learning criterion, both known 2025 winners wrote ~2,500 structured words, and it is
   the most underrated deliverable in this entire event.

**Two things to monitor, not act on yet:** the **Judges tab** (the panel is not yet published —
if it shifts toward environmental domain experts, re-weight toward scientific defensibility)
and the **Updates tab / Discord** for a possible **Kinetik** category announcement.

---

## Appendix — where the evidence is thin, stated plainly

- **The 2026 judging panel is unpublished.** All judge analysis is inference from the 2024 and
  2025 panels, which were recruited through the same open volunteer form. High-confidence
  prior, not fact.
- **Default-solution prevalence percentages are estimates, not counts.** Devpost's project
  search is JavaScript-rendered and returned empty to both `curl` (403, WAF-blocked) and
  WebFetch. The structural clustering claim is supported by the 2025 gallery; the specific
  percentages are calibrated judgment.
- **Submission-count projection (50–70)** extrapolates a single year's conversion rate
  (885 → 98). One data point.
- **P4's evidence base leans on solar-industry vendor blogs** with a commercial interest in the
  problem existing, offset by two independent patents. This is why it scored 4 and not 5 on
  Pain Evidence.
- **No "Best Use of X" prizes were found for 2026.** The resources page explicitly says to
  check back for updates, so this may change before the deadline.
