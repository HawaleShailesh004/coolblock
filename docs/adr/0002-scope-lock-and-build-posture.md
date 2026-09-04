# 2. Scope lock and build posture for Phase 0

Date: 2026-09-04

## Status

Accepted

## Context

COOLBLOCK-BUILD-PLAN.md §17 leaves four open decisions, the first of which
blocks Phase 1. They were resolved at the start of the build.

## Decision

1. **Neighborhood:** Edison-Eastlake, Phoenix, AZ (the plan's recommendation).
   Recorded in `config/neighborhood.toml`, per the scope lock in §1.3 — not
   revisited before Phase 15.
2. **Team:** Solo, agent-driven. The four lanes in §11 are run sequentially/via
   subagents rather than assigned to separate humans.
3. **Claude API:** available now (`ANTHROPIC_API_KEY` to be supplied via
   `.env`, not committed). Wolfram Cloud licence not yet in hand — §7.2 drops
   to a stretch goal; `engine.verify` ships with the fallback noted in the
   plan (a second, independent Python solver in place of the Wolfram
   `NMaximize` cross-check) until credentials land.
4. **Infra provisioning (Vercel/Fly.io/Neon/R2/Clerk/domain):** deferred.
   Phase 0 targets local-only via `docker-compose.yml` (Postgres+PostGIS+pgvector,
   Redis, MinIO as an R2 stand-in, TiTiler). Cloud provisioning is a follow-up
   pass once local `make dev` is proven, not a Phase 0 blocker.

## Consequences

- `config/neighborhood.toml` is the only place the target city is named.
- `engine/verify` must be written against an interface that tolerates a
  missing Wolfram credential without failing the rest of the pipeline —
  checked at Phase 6/10 rather than assumed.
- The Phase 0 DoD ("a styled hello page deploys to coolblock.xyz from main")
  is descoped to "the app runs locally via `make dev`" until infra
  provisioning happens; the domain claim and cloud deploy remain open
  follow-ups tracked here, not silently dropped.
