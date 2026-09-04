# NextStep Hacks 2026 — Hackathon Strategy Brief

**Theme:** Earth Forward  
**Deadline:** September 13, 2026, 5:00 PM EDT  
**Participants:** 502 (as of Sep 3)  
**Format:** Online, ~3 weeks (Aug 21 – Sep 13)  
**Organizer:** HackAlphaX (student-led nonprofit)

---

## PHASE 1 — HACKATHON INTELLIGENCE BRIEF

### 1a. Theme Decoding

"Earth Forward" is an environmental-tech theme. The description explicitly lists: climate resilience, renewable energy, conservation, sustainable agriculture, waste reduction. The key phrase is **"identify a pressing environmental problem affecting your community or the world."** This is intentionally broad — any environmental angle qualifies. The encouragement to "collaborate with local organizations, environmental groups, researchers, or community members" signals judges reward **grounded, community-connected solutions** over abstract global platforms.

**What the theme implicitly favors:** tangible, demonstrable environmental impact on a specific community or user group. Not policy papers, not awareness campaigns — working tools that address a specific pain point.

**Disqualifiers/constraints:** Students only, ages 13+. Companies/professional orgs excluded. Old projects allowed only if you clearly delineate pre-hackathon vs. during-hackathon work.

### 1b. Participant Density Read

502 participants is moderate for a Devpost hackathon. In past years: 2025 had 885, 2024 had a similar scale. Actual submissions will be far fewer — typically 15-25% of registrants submit. Expect **~75-125 submissions.**

At this count, a polished, technically impressive project with a clear problem statement stands out. The average team is high-school students, many first-time hackers (the event is tagged "Beginner Friendly"). The quality floor is low — many submissions will be concept pitches, half-working prototypes, or generic "awareness" apps. **A fully functional demo with real data wins on completion alone.**

### 1c. Prize Structure Full Parse

| Prize | Cash | Extras | Winners |
|-------|------|--------|---------|
| 1st Place | $1,000 | $500 Claude credits, Final Round Interview @ YC startup, 2 AOPS coupons, XYZ domains, 1yr NordVPN/NordPass/Saily/Incogni | 1 |
| 2nd Place | $500 | $250 Claude credits, 1 AOPS coupon, XYZ domains, 1yr Nord suite | 1 |
| 3rd Place | $250 | $100 Claude credits, 1 AOPS coupon, XYZ domains, 1yr Nord suite | 1 |
| Participation | — | Wolfram Alpha access ($830 value), XYZ domains | 700 |

**Key observations:**
- There is only **one track** ("Earth Forward") — no separate track prizes to optimize for. This simplifies strategy: win overall or don't.
- **No "Best Use of X" special prizes** are listed for 2026, unlike some past years. Claude is a sponsor but there's no "Best Use of Claude" prize. This means: use the best tools for the job, don't force sponsor integrations.
- The Claude credits as prizes signal the organizers value AI-powered projects. Using Claude/AI effectively in your solution is a soft signal to judges.
- The YC startup interview for 1st place signals the organizers value **entrepreneurial framing** — projects that could become real products.

### 1d. Submission Requirements as Design Constraints

Required deliverables:
1. **Video demo/pitch ≤ 5 minutes** → Solution must be demo-able in video. No backend-only tools. Must have a visual interface or clear visual output. The 5-min cap rewards focused, tight narratives.
2. **Link to repository/code** → Code must be clean enough to inspect. Judges may or may not look, but messy repos signal low completion.
3. **Link to live website/app (if applicable)** → A live deployment is a differentiator. Solutions that work in a browser win over "run locally" instructions.

**Constraint list (all solutions must satisfy):**
- C1: Must produce a visual, demo-able interface (web or mobile)
- C2: Must be deployable/accessible live (strong advantage)
- C3: Must tell a clear 3-minute story (problem → solution → demo) with 2 minutes for context/impact
- C4: Must have clean, inspectable code repository
- C5: Must address the "Earth Forward" environmental theme directly
- C6: Must clearly delineate what was built during the hackathon period

### 1e. Technology Deep Read

No specific required technologies or sponsor SDKs are mandated. The sponsors are:
- **Claude** — AI/LLM. Mature, excellent API, strong for text analysis/generation/agents. Deep integration = using it beyond a simple chatbot wrapper.
- **Wolfram** — Computation engine. Good for scientific/mathematical modeling. Participation prize only.
- **NordVPN/NordPass/Saily/Incogni** — Consumer privacy products. No technical integration expected.
- **XYZ Domains** — Domain registration. No integration.
- **Kinetik** — Listed as sponsor but no specific prize.
- **AOPS** — Math education. No integration.

**Strategic tech read:** Claude is the only sponsor with a technical product relevant to building. Using Claude's API deeply (multi-step reasoning, tool use, structured outputs) signals platform expertise. No other sponsor tech needs integration.

**Risk assessment:** All major web frameworks, APIs, and deployment platforms are stable. No experimental/controlled-availability risks. The only real risk is demo instability from poor deployment or flaky third-party APIs.

### 1f. Judge Intelligence — MANDATORY RESEARCH

The 2026 judges are listed only as **"HackAlphaX Team"** — no individual names. Based on research:

**Known HackAlphaX leadership (from past years and LinkedIn):**

1. **Aditya Kirubakaran** — Founder & Executive Director. Student. Led all past NextStep Hacks as lead organizer and judge. No published technical work found. High-school/college student focused on STEM accessibility.
   - *Evidence:* Named as judge in 2021, 2024; credited as founder on Devpost and hackalphax.co.
   - *Bias synthesis:* Values accessibility, social impact, beginner-friendliness. Will respond to projects that feel usable by non-technical people.

2. **Krishnan Shankar** — Technical & Operations Lead. Listed on LinkedIn as Technical Lead at HackAlphaX.
   - *Evidence:* Named as judge in 2021. LinkedIn profile found. Talent sources include FIRST Tech Challenge, HackTJ — signals robotics/hackathon background.
   - *Bias synthesis:* Technical background. Will evaluate whether the tech actually works and is well-architected.

3. **Samanyu Bansal** — Growth/Outreach Lead. High school student (John P. Stevens HS, Edison NJ). Skills listed as coding, math.
   - *Evidence:* LinkedIn profile, named as judge in 2021.
   - *Bias synthesis:* Younger judge, likely values creative presentation and clear communication.

4. **Keshav Majithia** — Financials Lead. Named in 2021 judging panel.
   - *Evidence:* Named in 2021. No further public profile found.
   - *Bias synthesis:* Not findable beyond title. Cannot assess.

**Past external judges (2021):** Vladislav Gukasov (Senior SWE), Albert Lie (ex-founding engineer Xendit/YC S15), Alexander Kozhenkov (Team Lead GridGain), plus several Russian-market developers. **It's unclear if external judges return for 2026 — the listing says only "HackAlphaX Team."**

**Panel Synthesis:**
- The panel is **student-led, non-specialist.** These are not domain experts in environmental science, ML, or any specific vertical. They're high-school/college students running a nonprofit hackathon.
- **What this panel rewards (evidence from past winners):**
  - 2025 winners: DyslexicAssist (reading accessibility), Memora (face blindness AI app), Eyelink (social connections) — all **human-centered, specific-user-group tools with clear AI integration and polished UX.**
  - 2024 winners: BizVision (AI for blind businesses), LocalHarvest (farmer marketplace), OrderMatic, MyMarket — **practical tools for specific communities, marketplace/utility focus.**
  - 2022 winners: MusicGenic (music production), Photo Cook (ingredient → recipe), MedChain (blockchain health) — **consumer-facing, clear value prop, demo-friendly.**
- **Pattern:** Winners are **specific-problem, specific-user, polished demo, clear AI/tech integration.** Not research projects, not dashboards, not awareness sites. The judges reward "I can see this being a real product."

---

## PHASE 2 — SOLUTION SPACE MAPPING

### 2a. Track Selection Decision

There is only one track: **Earth Forward (environmental).** No track selection needed. All analysis operates within this theme.

### 2b. Default Solution Mapping (what 40-60% of teams will build)

The default submission pattern for "Earth Forward" at this participant level:

> **"An eco-awareness web app that calculates your personal carbon footprint from a questionnaire, displays it on a dashboard with charts, and suggests generic tips to reduce it. May include a chatbot powered by an LLM that answers sustainability questions. Basic React/Next.js frontend, a few API calls, deployed on Vercel."**

Variants: recycling classifier (upload image → "plastic" or "glass"), tree-planting tracker, general "sustainability tips" chatbot, environmental news aggregator.

**This is the crowded center. Do not build this.**

### 2c. Existing Solution Landscape

Before claiming any gap, what already exists in the environmental-tech space:
- **Carbon calculators:** EPA Carbon Footprint Calculator, CoolClimate (Berkeley), Wren, Joro, Klima — dozens exist. Well-documented limitations (outdated emission factors, no standardization) but the space is saturated.
- **Recycling classifiers:** TrashBot, numerous hackathon projects. Overdone.
- **Air quality:** PurpleAir, AirNow, IQAir — extensive sensor networks and apps exist.
- **Water quality:** Limited consumer tools. EPA has databases but they're for public systems, not private wells. MyWell (limited), some state-specific portals. **Genuine gap here.**
- **Food waste:** Too Good To Go, Flashfood (surplus sales); Winnow, Leanpath (commercial kitchen tracking). Consumer household tools are weak.
- **Biodiversity monitoring:** iNaturalist, eBird, Seek — dominant but with well-documented limitations (sampling bias, poor offline support, accuracy issues).
- **Urban heat:** Academic research tools exist but no consumer-facing community tools. **Gap.**

---

## PHASE 3 — PROBLEM IDENTIFICATION

### Problem Pool (8 problems, scored on 6 dimensions, 1-5 each)

| # | Problem | Who | Why current solutions fail | A (Pain) | B (Gap) | C (Hack Fit) | D (Judge) | E (Feasibility) | F (Special) | **Total** |
|---|---------|-----|---------------------------|----------|---------|--------------|-----------|-----------------|-------------|-----------|
| 1 | **Private well water contamination blindness** | 23M US households on private wells who don't know what's in their water | EPA doesn't regulate private wells; testing is expensive ($100-300+), confusing, and most households don't test regularly. 40% of Iowa well owners never test. PFAS found in 20-95% of tested wells depending on region. | 5 | 5 | 5 | 4 | 4 | 2 | **25** |
| 2 | **Hyperlocal wildfire smoke exposure gaps** | Communities in wildfire-prone areas where regulatory monitors are miles away | Regulatory monitors miss neighborhood-scale variability; low-cost sensors exist but data interpretation requires expertise communities lack. Rural Alaska study: few hosts use sensor data for decisions despite having sensors. | 4 | 3 | 5 | 4 | 3 | 2 | **21** |
| 3 | **Urban heat island inequity mapping** | Low-income urban residents in heat-vulnerable neighborhoods | Satellite data exists but a "valley of death" between research and community action; <11% of 500+ publications engaged with affected communities. No consumer-facing tool translates thermal data into actionable neighborhood guidance. | 4 | 4 | 5 | 4 | 4 | 2 | **23** |
| 4 | **Household food waste from expiry confusion** | Consumers who throw away safe food due to confusing date labels ("best by" vs "use by" vs "sell by") | Existing apps require manual entry; receipt scanning is unreliable; shelf-life databases are incomplete; no tool connects what's in your fridge to actual spoilage science. | 4 | 3 | 4 | 4 | 5 | 2 | **22** |
| 5 | **Citizen science biodiversity data is biased and unusable** | Conservation researchers and land managers who need reliable local biodiversity data | iNaturalist data is spatially biased toward parks/urban areas, taxonomically biased toward charismatic species, and quality filtering destroys sample size. No tool helps communities run structured, gap-filling biodiversity surveys. | 4 | 4 | 4 | 3 | 4 | 2 | **21** |
| 6 | **Small-farm environmental monitoring is unaffordable** | Smallholder farmers in developing regions needing soil/weather data for decisions | Commercial IoT systems cost $1000s, need internet, and break without local repair. Open-source alternatives exist but require technical skill to deploy and interpret. | 4 | 3 | 4 | 3 | 3 | 2 | **19** |
| 7 | **Community water infrastructure decay is invisible** | Small-town residents served by aging municipal water systems | Lead service lines, aging pipes — but residents don't know their specific risk. Data exists in utility records but isn't accessible. | 3 | 3 | 4 | 3 | 3 | 2 | **18** |
| 8 | **Greenwashing in consumer products is hard to verify** | Eco-conscious consumers trying to make sustainable purchasing decisions | "Eco-friendly" labels are unregulated; consumers can't verify claims. FTC Green Guides exist but aren't consumer-accessible. | 3 | 3 | 4 | 4 | 5 | 2 | **21** |
| 9 | **Climate adaptation planning for small municipalities** | Small-town planners who lack resources for climate risk assessment | Large cities have climate plans; small towns (<50k pop) rarely do. Existing tools require GIS expertise. | 4 | 4 | 5 | 3 | 3 | 2 | **21** |
| 10 | **Microplastic exposure from household water/food is unmeasured** | Health-conscious households concerned about microplastic contamination | No consumer tool estimates microplastic exposure; research is fragmented across water, food, air pathways. | 4 | 4 | 4 | 3 | 3 | 2 | **20** |

**Top 3 by arithmetic:**
1. **#1 — Private well water contamination blindness (25)**
2. **#3 — Urban heat island inequity mapping (23)**
3. **#4 — Household food waste from expiry confusion (22)**

---

## PHASE 4 — TOP 3 PROBLEM DEEP DIVES

---

### PROBLEM 1: WellSafe — Private Well Water Risk Intelligence

**THE PROBLEM**

23 million US households rely on private wells for drinking water. The EPA has no authority to regulate or monitor them. Testing costs $100-300+ per contaminant panel, requires mailing samples to labs, and results come back in technical jargon most homeowners can't interpret. 40% of Iowa well owners never test at all. PFAS — linked to cancer, thyroid disease, and immune suppression — has been found in 20-95% of tested private wells depending on region. These households are flying blind on what's in their water, and disproportionately, it's low-income and minority communities who test least.

**EVIDENCE OF REAL PAIN**

1. **PFAS in Rural US Well Water (2025, Environmental Science & Technology):** "The vast majority of private well users lack information to guide decision-making about whether they should act to protect themselves… public health departments are typically understaffed and lack resources to support statewide testing." ([doi:10.1021/acs.est.5c02521](https://doi.org/10.1021/acs.est.5c02521))

2. **'Bad water just means bad health' — NC barriers study (2025, IOP Science):** Identified financial barriers, proximity to agricultural hazards, discrimination, knowledge gaps, and mistrust as systemic obstacles to safe drinking water in rural Eastern NC. ([doi:10.1088/2752-5309/ae4f17](https://beta.iopscience.iop.org/article/10.1088/2752-5309/ae4f17))

3. **Iowa Private Well Testing RCT (2024, ES&T):** "Around 40% of households do not regularly test, treat, or avoid their drinking water, suggesting pollution exposure may be widespread." Intervention increased testing but had limited impact on behavior change beyond that. ([doi:10.1021/acs.est.4c02835](https://pubs.acs.org/doi/full/10.1021/acs.est.4c02835))

4. **Private Well Water Safety clinical guidance (2025, JABFM):** "Low-income and less-educated households are also less likely to test or treat their well water, despite being at comparable risk for contamination. Even when free testing is available, participation is higher among more affluent populations." ([JABFM 38/6](https://www.jabfm.org/content/jabfp/38/6/1126.full.pdf))

5. **Tapwater contaminant mixtures study (2025, RSC):** "High analytical costs, limited technical training/awareness, and conflation of safety and aesthetic quality severely undermine homeowner private-well monitoring." ([doi:10.1039/D5EW00490J](https://pubs.rsc.org/en/content/articlehtml/2025/ew/d5ew00490j))

**EXISTING SOLUTIONS AND WHY THEY FAIL**

- **EPA's PFAS Analytic Tools:** Compiles data on potential PFAS sources nationally but "does not provide information about the likelihood of private well contamination arising from these sources or the distances over which they may influence contamination risk." Database, not a user tool.
- **State well-testing programs:** Exist in some states but chronically understaffed, only cover specific contaminants, and reach a fraction of households. Voluntary participation skews affluent.
- **MyWell / private well apps:** Sparse, typically just record-keeping. Don't do risk prediction or interpret results.
- **Home test kits (e.g., Tap Score):** Still $100-200+, still require mailing samples, still return results in technical format. Don't predict risk before you test.

**The gap:** No tool tells a private well owner "based on your location, well depth, surrounding land use, and known contamination sources, here is your estimated contamination risk profile and what you should test for first" — before they spend any money.

**PROPOSED SOLUTION DIRECTION**

**WellSafe** — an AI-powered well water risk assessment platform. Enter your address and answer 5-6 questions about your well (depth, age, nearby land use). The system cross-references:
- EPA PFAS source data and Superfund site locations (public APIs/databases)
- USGS groundwater quality data
- State agricultural land-use data
- Geological/aquifer vulnerability maps
- Known contamination incidents in the area

Claude AI synthesizes these data sources into a **personalized risk report** in plain language: "Your well is within 3 miles of an active agricultural operation and sits on a shallow aquifer. You have elevated risk for nitrate and pesticide contamination. Priority test: nitrate ($15 strip test, available at [link])."

**The winning demo in 3 minutes:** Show the map interface → enter an address → watch the risk layers light up → read the personalized report → see the prioritized, affordable testing recommendations with direct links. Then show the "interpret your results" feature: upload a lab report PDF, Claude extracts the values and explains what each means in context.

**Core insight that makes it different:** It's a *risk predictor* not a *test result recorder*. It tells you what to worry about before you spend money, using public environmental data that exists but has never been assembled into a consumer-facing tool.

**SPECIAL PRIZE STACK OPPORTUNITY**

No special-category prizes exist in 2026. Claude is a sponsor — deep, multi-step Claude integration (data synthesis, report generation, lab result interpretation) demonstrates genuine platform use, which may informally resonate.

**SUBMISSION REQUIREMENT FIT**

- C1 (Visual interface): ✅ Map-based UI with interactive risk layers + generated reports
- C2 (Live deployment): ✅ Standard web app, deployable on Vercel/Railway. No exotic dependencies.
- C3 (3-min story): ✅ Perfect narrative arc: "23M households don't know what's in their water → enter your address → here's your risk → here's what to do"
- C4 (Clean repo): ✅ Standard Next.js + API routes + Claude SDK architecture
- C5 (Earth Forward): ✅ Directly addresses water conservation and community health
- C6 (New work): ✅ Built from scratch during hackathon

**JUDGING CRITERION ALIGNMENT**

- **Originality:** High. Carbon calculators are everywhere; well-water risk predictors are not. This is not a standard hackathon project. Judges won't have seen it before.
- **Adherence to Track:** Full. Water safety is explicitly environmental; the community-engagement angle maps directly to the theme's call to "collaborate with local organizations."
- **Completion:** The architecture is straightforward (web app + public data APIs + Claude). A polished, working demo is achievable in 3 weeks with LLM-augmented development.
- **Learning:** Cross-referencing multiple public data sources, geospatial visualization, AI-powered report generation — all stretch areas.
- **Design:** Map-based interface with layered risk visualization is inherently visually compelling.
- **Technology:** Multi-source data fusion + Claude for synthesis and interpretation is technically impressive without being fragile.

**JUDGE RESONANCE ANALYSIS**

- **Aditya Kirubakaran (Founder):** Values accessibility and social impact. WellSafe serves an underserved population with a tool that requires no technical expertise. The "real product" feel aligns with past winner patterns.
- **Krishnan Shankar (Technical Lead):** Will appreciate the multi-data-source architecture and clean integration pattern.
- **General panel:** Student judges respond to projects that feel like they matter. "23 million households" is a number that lands. Past winners (BizVision for blind businesses, DyslexicAssist, Memora for face blindness) all targeted underserved populations.

**HONEST RISK FLAGS**

- **Data availability:** USGS, EPA, and Superfund data are public but may require scraping or bulk downloads. Verify data coverage for the demo region in the first 48 hours.
- **Geospatial accuracy:** Risk prediction quality depends on proximity calculations and aquifer data resolution. May need to simplify to county-level for the demo rather than parcel-level.
- **Regulatory disclaimer:** Must include "this is not a substitute for professional testing" prominently. Judges in student hackathons are unlikely to penalize this, but it's good practice.

**INTEGRATION RISK FLAGS**

- **Public data APIs:** EPA and USGS APIs are well-documented and stable. Low risk.
- **Claude API:** Mature, reliable. Used for text synthesis (its sweet spot). Low risk.
- **Geocoding:** Google Maps/Mapbox APIs are stable. Low risk.
- **Most likely demo failure:** Data coverage gap for a specific address entered during judging. **Mitigation:** Pre-load data for several demo regions and gracefully handle "insufficient data" cases.

**COMPETITIVE POSITIONING**

Why other teams won't build this: it requires understanding environmental data sources (USGS, EPA PFAS tools, aquifer maps) and how to combine them — knowledge most high-school hackers don't have. The default "environmental" project is a carbon calculator or recycling app. The non-obvious angle: using *existing public data* that's never been made consumer-accessible, rather than collecting new data. The barrier to replication: the data fusion logic and the domain knowledge to make the risk assessment meaningful.

---

### PROBLEM 2: HeatMap — Neighborhood Heat Vulnerability Intelligence

**THE PROBLEM**

Urban heat islands kill more Americans annually than any other weather event. Low-income neighborhoods — often with less tree cover, more asphalt, and older housing without AC — experience temperatures 5-15°F higher than affluent areas in the same city. Satellite thermal data now exists at block-level resolution (ECOSTRESS, Landsat), but a review of 500+ scientific publications found only 10.9% engaged with the communities being analyzed. The data exists; the translation to community action doesn't.

**EVIDENCE OF REAL PAIN**

1. **"Valley of death" in urban heat research (2025):** Review of 500+ publications: "We identify a critical lack of engagement with the communities being analyzed (10.9%; n = 58); yet, community engagement is key to bridging analysis with subsequent action." ([doi:10.1177/19394071251413391](https://doi.org/10.1177/19394071251413391))

2. **UHI policy implementation in 5 cities (2025, Royal Society):** "While UHI science has advanced, its knowledge and practice translation into real-life practice remains limited… findings emphasize the importance of simple and user-friendly tools for planners." ([doi:10.1098/rsta.2024.0581](https://doi.org/10.1098/rsta.2024.0581))

3. **Bridging the application gap (2026):** "The root cause of this application impasse lies not in a deficit of external tools but in the reductionist mindset of the knowledge producers." ([doi:10.1177/2754124x261447620](https://doi.org/10.1177/2754124x261447620))

4. **Climate services reframing study:** "Climate service providers often struggle to respond to users other than a small cadre of actors like themselves." ([doi:10.1016/S2405-8807](https://www.sciencedirect.com/science/article/pii/S2405880721000157))

**EXISTING SOLUTIONS AND WHY THEY FAIL**

- **NASA ECOSTRESS Explorer:** Provides raw thermal imagery. Requires GIS expertise. No actionable guidance.
- **Heat.gov (NIHHIS):** Federal resource with heat risk maps. Coarse resolution, not neighborhood-specific.
- **Academic heat-equity maps:** Published in journals, not accessible to residents or community organizers.

**The gap:** No consumer-facing tool says "your specific block is X degrees hotter than the city average, here's why (asphalt ratio, tree canopy deficit, building density), and here are the specific interventions that would help most."

**PROPOSED SOLUTION DIRECTION**

**HeatMap** — a neighborhood heat vulnerability tool. Enter an address → see your block's heat risk score derived from:
- Landsat/ECOSTRESS surface temperature data (public, NASA)
- Tree canopy coverage (NLCD, local data)
- Impervious surface percentage
- Census income/demographic data (vulnerability overlay)
- AC penetration estimates

Claude generates a **neighborhood heat profile** in plain language with specific, ranked intervention recommendations (tree planting locations, cool-roof eligibility, cooling center proximity).

**Demo flow:** Enter address → animated heat map renders → neighborhood profile appears → "Your block is 8°F hotter than the city median because of 72% impervious surface and 11% canopy cover. Top intervention: 15 street trees on Main St would reduce peak temperature by ~3°F."

**SUBMISSION REQUIREMENT FIT**

All constraints satisfied. Visually spectacular (heat maps are inherently compelling in demos). Clean narrative arc. Standard web architecture.

**JUDGING CRITERION ALIGNMENT**

- **Originality:** High for a student hackathon. Heat equity mapping is an active research area but has never been built as a consumer tool.
- **Adherence to Track:** Direct — climate resilience, environmental justice.
- **Design:** Heat maps are visually stunning. This project demos better than almost anything else.
- **Technology:** Satellite data processing + AI synthesis is technically impressive.

**JUDGE RESONANCE ANALYSIS**

Same student panel. Environmental justice angle is strong. Visually impressive demos win with non-specialist judges.

**HONEST RISK FLAGS**

- **Satellite data processing:** ECOSTRESS/Landsat data requires geospatial processing (rasterio, GDAL). This is the hardest 20% — LLMs can generate the code but debugging projection issues is time-consuming. **Validate in first 48 hours.**
- **Data download size:** Satellite imagery is large. May need to pre-process a few demo cities rather than offer nationwide coverage.
- **Resolution limitations:** Surface temperature ≠ air temperature. Must be transparent about approximation.

**INTEGRATION RISK FLAGS**

- **NASA Earthdata API:** Requires registration, bulk downloads can be slow. Medium risk — pre-download for demo regions.
- **Geospatial libraries in browser:** Heavy. Consider server-side processing with pre-rendered tiles.
- **Most likely demo failure:** Satellite tile loading timeout. **Mitigation:** Pre-render demo city tiles as static assets.

**COMPETITIVE POSITIONING**

Satellite data processing is a genuine technical barrier for high-school teams. The environmental-justice framing is distinctive. Risk: a team with GIS experience could build something similar, but unlikely at this participant level.

---

### PROBLEM 3: FreshLens — AI Expiry Intelligence for Zero Food Waste

**THE PROBLEM**

US households waste ~30-40% of food purchased, much of it because of confusion about date labels. "Best by," "sell by," and "use by" mean different things — only "use by" relates to safety — but most consumers treat them all as hard expiry dates. The USDA estimates Americans waste $444 per person annually on food they throw away while still safe. Existing food-tracking apps require tedious manual entry of every item, have incomplete shelf-life databases, and don't account for how food was stored.

**EVIDENCE OF REAL PAIN**

1. **Food waste tracking accuracy study (2025):** "Technology alone might not resolve reporting errors if the personnel interacting with the systems lack the capacity, time, clarity or incentive to report accurately." Systems suffer from systematic underreporting and data quality issues. ([exa.ai/library/publication/592zr4p3gdt](https://exa.ai/library/publication/592zr4p3gdt))

2. **IoT food waste review (MDPI Sustainability 2023):** Identified data quality, lack of standardization, security, and battery/connectivity challenges as persistent barriers across the food supply chain. ([doi:10.3390/su15043482](https://www.mdpi.com/2071-1050/15/4/3482))

3. **Hackathon postmortem — "freshly yours" (Technica 2025):** "Determining which items were actually food was difficult without leveraging an API to parse and verify the data." Receipt scanning faced CORS issues, Next.js incompatibilities. Real developer friction in this space. ([github.com/candace-sun/technica-2025](https://github.com/candace-sun/technica-2025))

4. **Re-Plate food donation platform:** "Food labels vary in format, location, and clarity, making them hard to extract." Required combining vision + OCR in a single pipeline. ([github.com/Arjun-Mishra-312/re-plate](https://github.com/Arjun-Mishra-312/re-plate))

**EXISTING SOLUTIONS AND WHY THEY FAIL**

- **Too Good To Go / Flashfood:** Surplus marketplace for businesses. Not for household waste reduction.
- **Fridgely / NoWaste / similar apps:** Manual entry of every item. Poor UX kills adoption. Shelf-life estimates are generic (not storage-condition aware).
- **Receipt scanning apps:** Unreliable parsing, especially for non-standard formats. Don't map to actual food items reliably.

**The gap:** No tool lets you point your camera at your fridge/pantry and get an AI-powered assessment of what's actually safe to eat, what needs to be used first, and what recipes to make with items approaching real (not label) expiry.

**PROPOSED SOLUTION DIRECTION**

**FreshLens** — point your phone camera at food items or your open fridge. Claude Vision identifies items, estimates actual remaining freshness based on item type + storage conditions (not just label date), and generates a prioritized "use first" list with recipe suggestions using what needs to go.

**Demo flow:** Open app → snap a photo of fridge contents → AI identifies items with freshness estimates → "Your bell peppers have ~2 days left. Your yogurt is fine until next week (the 'best by' date is a quality marker, not safety). Tonight's suggestion: stuffed peppers with the ground beef and peppers."

**SUBMISSION REQUIREMENT FIT**

All constraints satisfied. Highly demo-friendly — "watch me point at my fridge" is immediately engaging. Mobile-first or web app with camera. Deployable.

**JUDGING CRITERION ALIGNMENT**

- **Originality:** Medium-high. Food waste apps exist, but vision-first + real-expiry intelligence is a new angle. Risk: judges may perceive it as "another food waste app" if not positioned carefully.
- **Adherence to Track:** Direct — waste reduction is explicitly listed in the theme.
- **Completion:** Achievable. Camera → Claude Vision → structured output → recipe API. Clean pipeline.
- **Design:** Camera-first UX is modern and engaging.
- **Technology:** Claude Vision for food identification is technically interesting.

**JUDGE RESONANCE ANALYSIS**

Past winner "Photo Cook" (2022, 2nd place) was literally "take a picture of ingredients → get recipe." FreshLens is an evolution of this exact pattern. The judges have rewarded this UX before.

**HONEST RISK FLAGS**

- **Claude Vision accuracy for food items:** May struggle with ambiguous items (which cheese is that?). Test thoroughly in first 48 hours.
- **"Just another food waste app" perception:** Must nail the positioning — lead with the "your food is safe, stop throwing it away" insight, not the tracking.
- **Recipe generation quality:** If recipes feel generic, the demo falls flat. May need curated fallbacks.

**INTEGRATION RISK FLAGS**

- **Claude Vision API:** Mature, reliable. Medium risk on accuracy for specific food items but the API itself is stable.
- **Recipe API (Spoonacular/Edamam):** Well-documented, stable. Low risk.
- **Camera access in browser:** WebRTC is mature but can be finicky across browsers. Test on multiple devices.
- **Most likely demo failure:** Camera permission issues on the demo device. **Mitigation:** Have pre-captured images as fallback input.

**COMPETITIVE POSITIONING**

Photo Cook won 2nd in 2022 — so this exact UX pattern has proven viability. The differentiation is the *expiry intelligence* layer (not just "what can I cook" but "what's actually still safe and what should I prioritize"). Risk: if other teams build Photo Cook clones, you're competing in a cluster. The "expiry science" angle is the moat.

---

## PHASE 5 — FINAL RECOMMENDATION

**Bet on Problem #1: WellSafe — Private Well Water Risk Intelligence.**

Here's why. First, it has the highest total score (25) by a clear margin, driven by exceptional pain evidence (5 peer-reviewed studies from 2024-2025 documenting the exact problem) and the widest solution gap (no consumer tool does this — period). Second, the architecture is the most demo-stable of the three: it's a web app querying public APIs and feeding results to Claude for synthesis, with no camera dependencies, no satellite imagery processing, and no ambiguous computer vision. Third, it's the most original for this hackathon context — the judges will have seen food waste apps (Photo Cook won in 2022) and dashboard-style visualizations, but they will not have seen a well water risk predictor. Fourth, the narrative is devastating in a 3-minute video: "23 million Americans don't know what's in their water. EPA can't help them. Enter your address. Now you know." That lands with student judges who value social impact. Fifth, the Claude integration is deep and natural — not a chatbot wrapper, but a multi-source data synthesizer and plain-language report generator — which resonates with Claude being a sponsor. The single biggest risk is data coverage: if the demo address falls in a gap, the experience breaks. Manage this by pre-loading complete data for 3-4 demo regions (pick counties with known contamination for dramatic effect) and building a graceful "insufficient data" fallback. In the first 72 hours: (1) verify EPA PFAS source API and USGS groundwater data API access and coverage, (2) build and validate the geocoding → data fusion pipeline for one demo county, (3) get Claude generating a compelling sample report from real data. If data access works, this project wins.
