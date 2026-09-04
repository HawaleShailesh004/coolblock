# 1. Record architecture decisions

Date: 2026-09-04

## Status

Accepted

## Context

CoolBlock is built across a compressed 9-day schedule with parallel agent
lanes (COOLBLOCK-BUILD-PLAN.md §11). Decisions made under time pressure are
exactly the ones that get silently reversed or contradicted later unless
they're written down at the moment they're made.

## Decision

We will use Architecture Decision Records, as described by Michael Nygard,
for architecturally significant decisions made during this project.

Each ADR is a single markdown file in `docs/adr/`, numbered sequentially,
named `NNNN-title-with-dashes.md`. An ADR is never edited after its status
moves to Accepted — a changed decision gets a new ADR that supersedes it.

## Consequences

Future contributors (or a returning agent lane) can see not just what was
decided but why, without re-deriving it from commit archaeology.
