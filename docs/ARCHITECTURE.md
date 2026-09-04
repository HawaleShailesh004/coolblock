# CoolBlock — Architecture

> Status: Phase 0 skeleton. Filled in as each phase lands; see
> [`COOLBLOCK-BUILD-PLAN.md`](../COOLBLOCK-BUILD-PLAN.md) for the authoritative
> design. This document is the living, shorter reference; the build plan is
> the long-form rationale. Decisions get recorded as ADRs in [`adr/`](adr/) as
> they're made, not reconstructed after the fact.

## 1. System overview

See COOLBLOCK-BUILD-PLAN.md §4 for the full data-flow diagram. In one sentence:
external sources are fetched once and cached (`engine.ingest`), the expensive
geospatial pipeline runs offline per neighborhood (`engine.thermal` →
`engine.surface` → `engine.impact`/`engine.equity` → candidate generation),
and the only thing a user triggers live is a fast re-solve
(`engine.optimize`) over the precomputed candidate set.

## 2. The three runtime paths

| Path | Trigger | Latency | Status |
|---|---|---|---|
| Cold pipeline | New neighborhood ingested | 20–90 min, offline | Not yet built (Phase 1) |
| Warm solve | User changes budget/constraints | 2–8 s, streamed | Not yet built (Phase 6/7) |
| Read | Loading a saved plan or public link | < 400 ms | Not yet built (Phase 7) |

## 3. Repo layout

See the repo root and COOLBLOCK-BUILD-PLAN.md §3.4 — the layout there is
current as of Phase 0.

## 4. Agent lanes

Four lanes, one shared contract (`packages/schema`, generated from the
FastAPI OpenAPI schema — never hand-written). See COOLBLOCK-BUILD-PLAN.md
§11 for the full lane/phase mapping.

## 5. Decisions

Architecture-significant decisions are recorded in [`adr/`](adr/), one file
per decision, never edited after acceptance (superseded by a new ADR
instead). Start with [`adr/0001-record-architecture-decisions.md`](adr/0001-record-architecture-decisions.md).
