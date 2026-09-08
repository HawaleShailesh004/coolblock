/**
 * Phase 8 -- the frontend's client for the real FastAPI backend built in
 * Phase 7 (apps/api). Typed against `@coolblock/schema`'s generated
 * OpenAPI types (§11: the FRONT/PLATFORM contract), not hand-written
 * response shapes.
 *
 * **Auth**: no Clerk tenant is provisioned yet
 * (docs/adr/0016-auth-dev-fallback-and-clerk-integration.md), so every
 * request carries the same `X-Dev-*` headers the backend's documented
 * local-dev fallback expects -- identical to the curl example in
 * docs/RUNNING-AND-TESTING.md §8. Swapping in real Clerk auth later is a
 * change to `authHeaders()` alone; nothing else in this file assumes the
 * dev-header shape.
 */
import type {
  Annotation,
  AnnotationCreate,
  ConstraintsIn,
  Memo,
  ParsedConstraints,
  Plan,
  PlanCreate,
  ScenarioVersion,
  ScenarioVersionDetail,
  ShareLink,
} from "@coolblock/schema";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DEV_USER_ID = "demo-user";
const DEV_WORKSPACE_ID = "demo-workspace";

export function authHeaders(): Record<string, string> {
  return {
    "X-Dev-User-Id": DEV_USER_ID,
    "X-Dev-Workspace-Id": DEV_WORKSPACE_ID,
    "X-Dev-Role": "owner",
  };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function listPlans(): Promise<Plan[]> {
  return apiFetch("/plans");
}

export function createPlan(body: PlanCreate): Promise<Plan> {
  return apiFetch("/plans", { method: "POST", body: JSON.stringify(body) });
}

export function updatePlanBudgetAndConstraints(
  planId: string,
  budgetUsd: number,
  constraints: ConstraintsIn,
): Promise<Plan> {
  return apiFetch(`/plans/${planId}`, {
    method: "PATCH",
    body: JSON.stringify({ budget_usd: budgetUsd, constraints }),
  });
}

export function solvePlan(planId: string): Promise<ScenarioVersion> {
  return apiFetch(`/plans/${planId}/solve`, { method: "POST" });
}

export function getScenario(planId: string, version: number): Promise<ScenarioVersionDetail> {
  return apiFetch(`/plans/${planId}/scenarios/${version}`);
}

export function createShareLink(planId: string, version: number): Promise<ShareLink> {
  return apiFetch(`/plans/${planId}/scenarios/${version}/share`, { method: "POST" });
}

/** §9 ★5: EWCB per strategy (spread_evenly/worst_first/squeaky_wheel/tes_score_only/coolblock), same budget. Real cost, ~15-20s. */
export function compareBaselines(planId: string, version: number): Promise<Record<string, number>> {
  return apiFetch(`/plans/${planId}/scenarios/${version}/baselines`);
}

export type LlmProvider = "anthropic" | "groq";
export type MemoProvider = LlmProvider;

/** §7.1 L1: NL -> optimizer constraints, via a real tool-use loop that resolves named places against the real cached OSM data (docs/adr/0020-*.md). Real API cost per call. */
export function parseConstraints(text: string, provider?: LlmProvider): Promise<ParsedConstraints> {
  return apiFetch("/plans/parse-constraints", {
    method: "POST",
    body: JSON.stringify({ text, provider: provider ?? null }),
  });
}

/** §7.1 L3/L6: the council memo, verified by the numeric provenance guard. Real API cost per call -- not cached client-side across re-renders, only re-fetched when the user explicitly asks again. `provider` overrides the backend's MEMO_LLM_PROVIDER default for this one call (docs/adr/0019-*.md). */
export function generateMemo(
  planId: string,
  version: number,
  includeBaselines = false,
  provider?: MemoProvider,
): Promise<Memo> {
  const params = new URLSearchParams({ include_baselines: String(includeBaselines) });
  if (provider) params.set("provider", provider);
  return apiFetch(`/plans/${planId}/scenarios/${version}/memo?${params.toString()}`, { method: "POST" });
}

export function listAnnotations(planId: string): Promise<Annotation[]> {
  return apiFetch(`/plans/${planId}/annotations`);
}

export function createAnnotation(planId: string, body: AnnotationCreate): Promise<Annotation> {
  return apiFetch(`/plans/${planId}/annotations`, { method: "POST", body: JSON.stringify(body) });
}

export function scenarioEventsUrl(planId: string, version: number): string {
  return `${API_BASE_URL}/plans/${planId}/scenarios/${version}/events`;
}

export function scenarioExportUrl(planId: string, version: number, format: "geojson" | "csv"): string {
  return `${API_BASE_URL}/plans/${planId}/scenarios/${version}/export.${format}`;
}
