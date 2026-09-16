# CoolBlock — Architecture

> The living, shorter reference. [`COOLBLOCK-BUILD-PLAN.md`](../COOLBLOCK-BUILD-PLAN.md)
> is the long-form design rationale; [`docs/adr/`](adr/) is where each
> architecture-significant decision actually got made, one file per
> decision, never edited after acceptance.

## 1. The one idea that shapes everything else

The expensive work (satellite imagery, geospatial modeling, impact/equity
scoring) is **precomputed once per neighborhood, offline**. Everything a user
triggers live — dragging a budget slider, adding a constraint — is a **fast
re-solve over an already-scored candidate set**. This single design choice is
why the live optimizer's progress animation can be real (it's really
solving, in ~2 seconds) rather than a fake loading bar over a cached result.

## 2. System diagram

```mermaid
flowchart TB
    subgraph External["External data sources"]
        direction LR
        Landsat["Landsat 8/9\n(surface temp)"]
        Sentinel["Sentinel-2\n(NDVI/NDBI)"]
        OSM["OpenStreetMap\n(buildings, roads, trees)"]
        Census["Census ACS +\nCDC SVI"]
        Parcels["Maricopa County\nparcels"]
    end

    subgraph Engine["engine/ (Python, installable package)"]
        direction TB
        Ingest["engine.ingest\ncached, checksummed, versioned"]
        Thermal["engine.thermal\nTsHARP downscaling + A3 validation"]
        Surface["engine.surface\nplantable candidates, ownership"]
        Impact["engine.impact / engine.equity\ncooling kernel, shade, HVI, EWCB"]
        Optimize["engine.optimize\nbest_plan: exact MILP → CELF fallback"]
        Narrate["engine.narrate\nLLM memo + numeric provenance guard"]
        Ingest --> Thermal --> Surface --> Impact --> Optimize
        Optimize --> Narrate
    end

    subgraph Storage["data/derived/&lt;neighborhood&gt;/"]
        Derived[("candidates.geojson,\nheat_surface_*.tif,\nbasemap.pmtiles, …")]
    end

    subgraph API["apps/api — FastAPI"]
        direction TB
        REST["REST endpoints\nplans, scenarios, export, share"]
        Queue["ARQ worker\n(Redis-backed job queue)"]
        SSE["SSE stream\nstage → site → done, per solve"]
        DB[("Postgres + PostGIS\nplans, scenario versions, sites")]
        REST --> Queue --> SSE
        REST --> DB
        Queue --> DB
    end

    subgraph Web["apps/web — Next.js"]
        direction TB
        Landing["Marketing homepage\n(static, real pipeline outputs)"]
        MapApp["/map — the live app\nbudget slider, constraints, table, export"]
    end

    External --> Ingest
    Surface --> Derived
    Impact --> Derived
    Derived --> Optimize
    Optimize -.->|"stream_solve()"| Queue
    SSE -->|"fetch-based SSE client"| MapApp
    REST --> MapApp
    Derived -.->|"static export"| Landing
```

## 3. The three runtime paths

| Path | Trigger | Latency | What runs |
|---|---|---|---|
| **Cold pipeline** | A new neighborhood is ingested | 20–90 min, offline, run once | Every `engine.ingest`/`engine.thermal`/`engine.surface`/`engine.impact` module, in order, writing `data/derived/<neighborhood>/` |
| **Warm solve** | A user changes the budget or a constraint | ~2 s, streamed | `engine.optimize.plan_service.stream_solve()` reads the cached candidates, solves (exact MILP or CELF fallback), streams stage/site/done events over SSE |
| **Read** | Loading a saved plan or a public share link | < 400 ms | A plain Postgres read — no solve, no pipeline |

## 4. The optimizer's own decision (docs/adr/0028)

```mermaid
flowchart LR
    A["Candidate pool for this\nprogram + land filter"] --> B{"≤ 1,000\ncandidates?"}
    B -- no --> C["CELF greedy\n(1-1/√e) worst-case guarantee"]
    B -- yes --> D["Exact MILP (HiGHS),\n10s wall-clock limit"]
    D --> E{"Proven optimal AND\n≥ CELF's value?"}
    E -- yes --> F["Use the exact plan\n(solver: exact_milp)"]
    E -- no --> C
    C --> G["Use the greedy plan\n(solver: celf)"]
    F --> H["order_by_contribution():\nrank sites by real marginal gain"]
    G --> H
```

Every plan producer — the live app, the five-baseline comparison, the static
map export — goes through this one function
(`engine/optimize/best_plan.py`), so the comparison chart can never score
CoolBlock against a weaker solver than what it actually hands a user.

## 5. Two programs, never ranked together (docs/adr/0027)

`trees` (street trees + park/lot tree clusters) and `cool_roofs` are separate
candidate pools with separate objectives. A tree's *ambient* cooling (spread
over the area around it) and a cool roof's *surface* cooling (at its own
footprint) are different physical quantities — ranked in one list, cool
roofs always win, and the "tree plan" the product is named for would contain
zero trees. The default plan is trees, on public land a city can actually
plant without an owner's consent.

## 6. Agent lanes

Four lanes, one shared contract (`packages/schema`, generated from the
FastAPI OpenAPI schema — never hand-written): the science engine, the API,
the web app, and the intelligence layer (LLM memo generation + its
provenance guard). See [`COOLBLOCK-BUILD-PLAN.md`](../COOLBLOCK-BUILD-PLAN.md) §11
for the full lane/phase mapping.

## 7. Decisions

Architecture-significant decisions are recorded in [`adr/`](adr/), one file
per decision, never edited after acceptance (superseded by a new ADR
instead). Start with [`adr/0001-record-architecture-decisions.md`](adr/0001-record-architecture-decisions.md).
