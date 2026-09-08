// Generated types land in ./generated/api.d.ts via `pnpm --filter @coolblock/schema generate`
// (apps/api must be running -- see docs/RUNNING-AND-TESTING.md). Do not hand-write API types
// here -- packages/schema is the single source of truth between the FRONT and PLATFORM lanes
// (§11); re-run `generate` and commit the diff whenever a router/schema changes shape.
import type { components } from "../generated/api";

export type { components, operations, paths } from "../generated/api";

export type Plan = components["schemas"]["PlanOut"];
export type PlanCreate = components["schemas"]["PlanCreate"];
export type PlanUpdate = components["schemas"]["PlanUpdate"];
export type ScenarioVersion = components["schemas"]["ScenarioVersionOut"];
export type ScenarioVersionDetail = components["schemas"]["ScenarioVersionDetailOut"];
export type ScenarioSite = components["schemas"]["ScenarioSiteOut"];
export type Annotation = components["schemas"]["AnnotationOut"];
export type AnnotationCreate = components["schemas"]["AnnotationCreate"];
export type ShareLink = components["schemas"]["ShareLinkOut"];
export type ConstraintsIn = components["schemas"]["ConstraintsIn"];
export type Memo = components["schemas"]["MemoOut"];
export type MemoNumber = components["schemas"]["MemoNumberOut"];
