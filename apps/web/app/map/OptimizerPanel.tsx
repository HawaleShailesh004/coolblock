"use client";

import { buildLiveSolutionLayer, type Layer, type LiveSolutionSite } from "@coolblock/map";
import type { PlaceResolution } from "@coolblock/schema";
import type { Geometry } from "geojson";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  authHeaders,
  compareBaselines,
  createPlan,
  createShareLink,
  downloadScenarioExport,
  getScenario,
  parseConstraints,
  scenarioEventsUrl,
  solvePlan,
  updatePlanBudgetAndConstraints,
  type LlmProvider,
} from "../../lib/api";
import { subscribeToEventStream, type EventStreamSubscription } from "../../lib/sse";
import { BaselineComparisonChart } from "./BaselineComparisonChart";
import { CouncilMemoPanel } from "./CouncilMemoPanel";

// Mirrors engine.optimize.plan_service's StageEvent/SiteEvent/DoneEvent
// dataclasses, exactly as coolblock_api/jobs/events.py serializes them to
// JSON (docs/adr/0017-*.md) -- not generated from the OpenAPI schema,
// since a StreamingResponse's SSE payload isn't part of FastAPI's schema.
interface StageEventData {
  stage: string;
  message: string;
}
interface SiteEventData {
  rank: number;
  candidate_id: string;
  intervention_type: string;
  cost_usd: number;
  marginal_gain_ewcb: number;
  cumulative_ewcb: number;
  cumulative_cost_usd: number;
  geometry: Geometry;
  properties: Record<string, unknown>;
}
interface DoneEventData {
  solver: string;
  n_sites: number;
  total_cost_usd: number;
  total_ewcb: number;
}
interface ErrorEventData {
  message: string;
}

type Status = "idle" | "creating" | "solving" | "done" | "error";

const MIN_BUDGET_USD = 5_000;
const MAX_BUDGET_USD = 500_000;
const BUDGET_STEP_USD = 5_000;
const DEFAULT_BUDGET_USD = 50_000;

const PLAN_PARAM = "plan";
const VERSION_PARAM = "version";

function readDeepLinkFromUrl(): { planId: string; version: number } | null {
  // This component is client-rendered but Next.js still server-renders it
  // once on the first request -- `window` doesn't exist there. Guarded
  // the same way `packages/map/src/viewState.ts` and `CoolBlockMap`'s own
  // mount effect keep every `window` access client-only.
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const planId = params.get(PLAN_PARAM);
  const versionRaw = params.get(VERSION_PARAM);
  if (!planId || !versionRaw) return null;
  const version = Number(versionRaw);
  if (Number.isNaN(version)) return null;
  return { planId, version };
}

function writeDeepLinkToUrl(planId: string, version: number): void {
  const url = new URL(window.location.href);
  url.searchParams.set(PLAN_PARAM, planId);
  url.searchParams.set(VERSION_PARAM, String(version));
  window.history.replaceState(null, "", url);
}

function siteToLiveSolutionSite(s: SiteEventData): LiveSolutionSite {
  return {
    rank: s.rank,
    candidateId: s.candidate_id,
    interventionType: s.intervention_type,
    costUsd: s.cost_usd,
    marginalGainEwcb: s.marginal_gain_ewcb,
    cumulativeEwcb: s.cumulative_ewcb,
    cumulativeCostUsd: s.cumulative_cost_usd,
    geometry: s.geometry,
    properties: s.properties,
  };
}

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const number0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

type Program = "trees" | "cool_roofs";

const PROGRAM_OPTIONS: { value: Program; label: string; hint: string }[] = [
  { value: "trees", label: "Trees", hint: "Street trees and park tree clusters: shade and cooling for people outside." },
  {
    value: "cool_roofs",
    label: "Cool roofs",
    hint: "Reflective roof coatings: a cooler home for the people inside. Private roofs need the owner's consent.",
  },
];

export function OptimizerPanel({ onLiveLayerChange }: { onLiveLayerChange: (layer: Layer | null) => void }) {
  const [budgetUsd, setBudgetUsd] = useState(DEFAULT_BUDGET_USD);
  // Trees on public land by default: what a heat-mitigation tree grant can
  // actually be spent on. Trees and cool roofs are never ranked against each
  // other -- their cooling isn't the same physical quantity (docs/adr/0027-*.md).
  // Mirrors ConstraintsIn's defaults in apps/api/src/coolblock_api/schemas.py.
  const [program, setProgram] = useState<Program>("trees");
  const [publicLandOnly, setPublicLandOnly] = useState(true);
  const [maxSitesPerZone, setMaxSitesPerZone] = useState<number | "">("");
  const [minSpendPerZoneUsd, setMinSpendPerZoneUsd] = useState<number | "">("");
  const [annualMaintenanceCapUsd, setAnnualMaintenanceCapUsd] = useState<number | "">("");
  const [mandatoryIncludeIds, setMandatoryIncludeIds] = useState<string[]>([]);
  const [mandatoryExcludeIds, setMandatoryExcludeIds] = useState<string[]>([]);

  // §7.1 L1: NL -> optimizer constraints (docs/adr/0020-*.md).
  const [constraintText, setConstraintText] = useState("");
  const [constraintProvider, setConstraintProvider] = useState<LlmProvider>("groq");
  const [parsingConstraints, setParsingConstraints] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [unsupportedRequests, setUnsupportedRequests] = useState<string[]>([]);
  const [placeResolutions, setPlaceResolutions] = useState<PlaceResolution[]>([]);

  // Initialized synchronously from the URL (not in an effect) so a deep
  // link's plan/version id is available on the very first render, with no
  // flash of the empty state while an effect catches up.
  const [planId, setPlanId] = useState<string | null>(() => readDeepLinkFromUrl()?.planId ?? null);
  const [version, setVersion] = useState<number | null>(() => readDeepLinkFromUrl()?.version ?? null);
  const [status, setStatus] = useState<Status>("idle");
  const [stageMessage, setStageMessage] = useState<string | null>(null);
  const [sites, setSites] = useState<SiteEventData[]>([]);
  const [summary, setSummary] = useState<DoneEventData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [baselineComparison, setBaselineComparison] = useState<Record<string, number> | null>(null);
  const [comparingBaselines, setComparingBaselines] = useState(false);
  const [baselineError, setBaselineError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const subscriptionRef = useRef<EventStreamSubscription | null>(null);

  useEffect(() => {
    return () => subscriptionRef.current?.close();
  }, []);

  useEffect(() => {
    onLiveLayerChange(sites.length > 0 ? buildLiveSolutionLayer(sites.map(siteToLiveSolutionSite)) : null);
    // onLiveLayerChange is a stable setter from the parent; only `sites` should retrigger this.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sites]);

  // Deep-link restore: if the URL already names a plan/version (a shared
  // link, or a reload after a solve), fetch its persisted result instead
  // of starting a new solve -- Phase 8 DoD: "deep links to any app state."
  useEffect(() => {
    const link = readDeepLinkFromUrl();
    if (!link) return;
    getScenario(link.planId, link.version)
      .then((scenario) => {
        const restoredSites: SiteEventData[] = scenario.sites.map((s) => ({
          rank: s.rank,
          candidate_id: s.candidate_id,
          intervention_type: s.intervention_type,
          cost_usd: s.cost_usd,
          marginal_gain_ewcb: s.marginal_gain_ewcb,
          cumulative_ewcb: s.cumulative_ewcb,
          cumulative_cost_usd: s.cumulative_cost_usd,
          geometry: s.geometry as unknown as Geometry,
          properties: s.properties,
        }));
        setSites(restoredSites);
        if (scenario.status === "done") {
          setStatus("done");
          setSummary({
            solver: scenario.solver ?? "",
            n_sites: restoredSites.length,
            total_cost_usd: scenario.cost_usd ?? 0,
            total_ewcb: scenario.objective_value_ewcb ?? 0,
          });
        } else if (scenario.status === "error") {
          setStatus("error");
          setErrorMessage(scenario.error_message ?? "solve failed");
        }
      })
      .catch(() => {
        // A stale/invalid deep link -- fall back to the idle state rather than erroring the whole page.
      });
    // Intentionally run once on mount only -- readDeepLinkFromUrl reads
    // window.location directly rather than depending on component state.
  }, []);

  const runOptimizer = useCallback(async () => {
    subscriptionRef.current?.close();
    setStatus("creating");
    setStageMessage(null);
    setSites([]);
    setSummary(null);
    setErrorMessage(null);
    setShareUrl(null);
    setBaselineComparison(null);
    setBaselineError(null);

    const constraints = {
      program,
      public_land_only: publicLandOnly,
      max_sites_per_zone: maxSitesPerZone === "" ? null : maxSitesPerZone,
      min_spend_per_zone_usd: minSpendPerZoneUsd === "" ? null : minSpendPerZoneUsd,
      annual_maintenance_cap_usd: annualMaintenanceCapUsd === "" ? null : annualMaintenanceCapUsd,
      mandatory_include_ids: mandatoryIncludeIds,
      mandatory_exclude_ids: mandatoryExcludeIds,
    };

    try {
      const plan = planId
        ? await updatePlanBudgetAndConstraints(planId, budgetUsd, constraints)
        : await createPlan({ name: "CoolBlock live plan", budget_usd: budgetUsd, constraints });
      setPlanId(plan.id);

      const scenario = await solvePlan(plan.id);
      setVersion(scenario.version_number);
      writeDeepLinkToUrl(plan.id, scenario.version_number);
      setStatus("solving");

      subscriptionRef.current = subscribeToEventStream(
        scenarioEventsUrl(plan.id, scenario.version_number),
        authHeaders(),
        (evt) => {
          if (evt.type === "stage") {
            setStageMessage((JSON.parse(evt.data) as StageEventData).message);
          } else if (evt.type === "site") {
            const site = JSON.parse(evt.data) as SiteEventData;
            setSites((prev) => [...prev, site]);
          } else if (evt.type === "done") {
            setSummary(JSON.parse(evt.data) as DoneEventData);
            setStatus("done");
          } else if (evt.type === "error") {
            setErrorMessage((JSON.parse(evt.data) as ErrorEventData).message);
            setStatus("error");
          }
        },
        () => {
          // A dropped connection mid-solve reconnects on its own (apps/web/lib/sse.ts);
          // nothing to surface here unless it never recovers, which the terminal
          // done/error event (or its absence) already communicates via `status`.
        },
      );
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "failed to start the solve");
    }
  }, [
    planId,
    budgetUsd,
    program,
    publicLandOnly,
    maxSitesPerZone,
    minSpendPerZoneUsd,
    annualMaintenanceCapUsd,
    mandatoryIncludeIds,
    mandatoryExcludeIds,
  ]);

  const runParseConstraints = useCallback(async () => {
    if (!constraintText.trim()) return;
    setParsingConstraints(true);
    setParseError(null);
    try {
      const result = await parseConstraints(constraintText, constraintProvider);
      setPublicLandOnly(result.constraints.public_land_only);
      setMaxSitesPerZone(result.constraints.max_sites_per_zone ?? "");
      setMinSpendPerZoneUsd(result.constraints.min_spend_per_zone_usd ?? "");
      setAnnualMaintenanceCapUsd(result.constraints.annual_maintenance_cap_usd ?? "");
      setMandatoryIncludeIds(result.constraints.mandatory_include_ids ?? []);
      setMandatoryExcludeIds(result.constraints.mandatory_exclude_ids ?? []);
      setUnsupportedRequests(result.unsupported_requests);
      setPlaceResolutions(result.place_resolutions);
    } catch (err) {
      setParseError(err instanceof Error ? err.message : "failed to parse constraints");
    } finally {
      setParsingConstraints(false);
    }
  }, [constraintText, constraintProvider]);

  const share = useCallback(async () => {
    if (!planId || version == null) return;
    const link = await createShareLink(planId, version);
    setShareUrl(`${window.location.origin}/share/${link.token}`);
  }, [planId, version]);

  const exportScenario = useCallback(
    async (format: "geojson" | "csv") => {
      if (!planId || version == null) return;
      setExportError(null);
      try {
        await downloadScenarioExport(planId, version, format);
      } catch (err) {
        setExportError(err instanceof Error ? err.message : `failed to export ${format}`);
      }
    },
    [planId, version],
  );

  const runBaselineComparison = useCallback(async () => {
    if (!planId || version == null) return;
    setComparingBaselines(true);
    setBaselineError(null);
    try {
      const result = await compareBaselines(planId, version);
      setBaselineComparison(result);
    } catch (err) {
      setBaselineError(err instanceof Error ? err.message : "failed to compare baselines");
    } finally {
      setComparingBaselines(false);
    }
  }, [planId, version]);

  const budgetSpent = sites.length > 0 ? (sites.at(-1)?.cumulative_cost_usd ?? 0) : 0;
  const isBusy = status === "creating" || status === "solving";

  return (
    <aside style={{ borderLeft: "1px solid var(--bg-2)", padding: 14, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
      <SectionLabel>Optimizer</SectionLabel>

      <div>
        <SectionLabel>Describe constraints (§7.1 L1)</SectionLabel>
        <textarea
          value={constraintText}
          disabled={isBusy || parsingConstraints}
          onChange={(e) => setConstraintText(e.target.value)}
          placeholder='e.g. "Keep it to public land only, prioritize sites near Booker T Washington School, cap annual maintenance at $8,000"'
          rows={3}
          style={{
            width: "100%",
            marginTop: 6,
            resize: "vertical",
            background: "var(--bg-1)",
            color: "var(--paper-0)",
            border: "1px solid var(--bg-2)",
            borderRadius: 4,
            padding: "6px 8px",
            fontSize: 11,
            fontFamily: "inherit",
          }}
        />
        <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
          <select
            value={constraintProvider}
            disabled={isBusy || parsingConstraints}
            onChange={(e) => setConstraintProvider(e.target.value as LlmProvider)}
            style={{ background: "var(--bg-1)", color: "var(--paper-0)", border: "1px solid var(--bg-2)", borderRadius: 4, padding: "4px 6px", fontSize: 11 }}
          >
            <option value="groq">Groq (fast)</option>
            <option value="anthropic">Claude (higher quality)</option>
          </select>
          <button
            onClick={runParseConstraints}
            disabled={isBusy || parsingConstraints || !constraintText.trim()}
            style={{
              flex: 1,
              background: "none",
              border: "1px solid var(--bg-2)",
              borderRadius: 6,
              color: "var(--paper-0)",
              cursor: parsingConstraints ? "default" : "pointer",
              padding: "4px 10px",
              fontSize: 11,
            }}
          >
            {parsingConstraints ? "Parsing..." : "Parse with AI"}
          </button>
        </div>
        {parseError && <p style={{ fontSize: 11, color: "var(--warn)", marginTop: 6 }}>{parseError}</p>}
        {placeResolutions.map((r, i) => {
          const candidateIds = r.candidate_ids ?? [];
          return (
            <p key={i} style={{ fontSize: 11, marginTop: 6, color: r.found ? "var(--ok)" : "var(--warn)" }}>
              {r.found
                ? `"${r.query}" -> ${r.matched_name} -- ${candidateIds.length} nearby site${candidateIds.length === 1 ? "" : "s"} included`
                : `"${r.query}" could not be found in the local map data`}
            </p>
          );
        })}
        {unsupportedRequests.map((note, i) => (
          <p key={i} style={{ fontSize: 11, marginTop: 6, color: "var(--warn)" }}>
            Not supported: {note}
          </p>
        ))}
      </div>

      <fieldset style={{ border: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6, fontSize: 12 }}>
        <legend style={{ opacity: 0.7, marginBottom: 6 }}>What are you funding?</legend>
        <div role="radiogroup" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
          {PROGRAM_OPTIONS.map((opt) => {
            const selected = program === opt.value;
            return (
              <label
                key={opt.value}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                  padding: "6px 8px",
                  borderRadius: 6,
                  border: `1px solid ${selected ? "var(--cool)" : "var(--bg-2)"}`,
                  background: selected ? "rgba(76,201,192,0.12)" : "transparent",
                  cursor: isBusy ? "default" : "pointer",
                }}
              >
                <input
                  type="radio"
                  name="program"
                  value={opt.value}
                  checked={selected}
                  disabled={isBusy}
                  onChange={() => {
                    setProgram(opt.value);
                    // A city can plant trees on its own land; a cool-roof program
                    // is mostly private homes, so don't silently keep a filter that
                    // would leave almost nothing to choose from.
                    setPublicLandOnly(opt.value === "trees");
                  }}
                  style={{ margin: 0 }}
                />
                {opt.label}
              </label>
            );
          })}
        </div>
        <span style={{ fontSize: 11, opacity: 0.6, lineHeight: 1.4 }}>
          {PROGRAM_OPTIONS.find((o) => o.value === program)?.hint}
        </span>
      </fieldset>

      <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
        <span style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ opacity: 0.7 }}>Budget</span>
          <span style={{ fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums" }}>{currency.format(budgetUsd)}</span>
        </span>
        <input
          type="range"
          aria-label="Budget"
          min={MIN_BUDGET_USD}
          max={MAX_BUDGET_USD}
          step={BUDGET_STEP_USD}
          value={budgetUsd}
          disabled={isBusy}
          onChange={(e) => setBudgetUsd(Number(e.target.value))}
          list="budget-ticks"
        />
        <datalist id="budget-ticks">
          <option value={5000} label="$5k" />
          <option value={50000} label="$50k" />
          <option value={200000} label="$200k" />
          <option value={500000} label="$500k" />
        </datalist>
      </label>

      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
        <input type="checkbox" checked={publicLandOnly} disabled={isBusy} onChange={(e) => setPublicLandOnly(e.target.checked)} />
        Public land only
      </label>

      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
        <span style={{ flex: 1 }}>Max sites per block group</span>
        <input
          type="number"
          min={1}
          placeholder="no cap"
          value={maxSitesPerZone}
          disabled={isBusy}
          onChange={(e) => setMaxSitesPerZone(e.target.value === "" ? "" : Number(e.target.value))}
          style={{ width: 64, background: "var(--bg-1)", color: "var(--paper-0)", border: "1px solid var(--bg-2)", borderRadius: 4, padding: "2px 6px" }}
        />
      </label>

      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
        <span style={{ flex: 1 }}>Annual maintenance cap</span>
        <input
          type="number"
          min={0}
          placeholder="no cap"
          value={annualMaintenanceCapUsd}
          disabled={isBusy}
          onChange={(e) => setAnnualMaintenanceCapUsd(e.target.value === "" ? "" : Number(e.target.value))}
          style={{ width: 64, background: "var(--bg-1)", color: "var(--paper-0)", border: "1px solid var(--bg-2)", borderRadius: 4, padding: "2px 6px" }}
        />
      </label>

      {(mandatoryIncludeIds.length > 0 || mandatoryExcludeIds.length > 0 || minSpendPerZoneUsd !== "") && (
        <p style={{ fontSize: 11, opacity: 0.7 }}>
          {mandatoryIncludeIds.length > 0 && `${mandatoryIncludeIds.length} site${mandatoryIncludeIds.length === 1 ? "" : "s"} mandatory-included`}
          {mandatoryIncludeIds.length > 0 && (mandatoryExcludeIds.length > 0 || minSpendPerZoneUsd !== "") && " · "}
          {mandatoryExcludeIds.length > 0 && `${mandatoryExcludeIds.length} excluded`}
          {mandatoryExcludeIds.length > 0 && minSpendPerZoneUsd !== "" && " · "}
          {minSpendPerZoneUsd !== "" && `${currency.format(minSpendPerZoneUsd)} min spend/zone`}
          {" (from constraint parsing)"}
        </p>
      )}

      <button
        onClick={runOptimizer}
        disabled={isBusy}
        style={{
          background: isBusy ? "var(--bg-2)" : "var(--cool)",
          color: isBusy ? "var(--paper-0)" : "var(--bg-0)",
          border: "none",
          borderRadius: 6,
          padding: "8px 10px",
          fontSize: 13,
          fontWeight: 600,
          cursor: isBusy ? "default" : "pointer",
        }}
      >
        {isBusy ? "Solving..." : "Run optimizer"}
      </button>

      <div role="status" aria-live="polite" style={{ fontSize: 12, minHeight: 16 }}>
        {status === "idle" && sites.length === 0 && (
          <span style={{ opacity: 0.55 }}>Set a budget and run the optimizer to see a ranked plan.</span>
        )}
        {status === "creating" && <span style={{ opacity: 0.75 }}>Creating plan...</span>}
        {status === "solving" && (
          <span style={{ opacity: 0.85 }}>
            {stageMessage ?? "Solving..."} &middot; site {sites.length} &middot;{" "}
            <span style={{ fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums" }}>
              {currency.format(budgetSpent)}
            </span>{" "}
            of {currency.format(budgetUsd)}
          </span>
        )}
        {status === "error" && <span style={{ color: "var(--warn)" }}>{errorMessage}</span>}
        {status === "done" && summary && (
          <span style={{ color: "var(--ok)" }}>
            {summary.n_sites} sites &middot; {currency.format(summary.total_cost_usd)} &middot;{" "}
            {number0.format(summary.total_ewcb)} EWCB ({summary.solver})
          </span>
        )}
      </div>

      {status === "done" && planId && version != null && (
        <div style={{ display: "flex", gap: 8, fontSize: 11 }}>
          <button
            onClick={() => exportScenario("geojson")}
            style={{ background: "none", border: "none", color: "var(--cool)", cursor: "pointer", padding: 0, font: "inherit" }}
          >
            Export GeoJSON
          </button>
          <button
            onClick={() => exportScenario("csv")}
            style={{ background: "none", border: "none", color: "var(--cool)", cursor: "pointer", padding: 0, font: "inherit" }}
          >
            Export CSV
          </button>
          <button onClick={share} style={{ background: "none", border: "none", color: "var(--cool)", cursor: "pointer", padding: 0, font: "inherit" }}>
            Share link
          </button>
        </div>
      )}
      {exportError && <p style={{ fontSize: 11, color: "var(--warn)", marginTop: 4 }}>{exportError}</p>}
      {shareUrl && (
        <input
          readOnly
          value={shareUrl}
          onFocus={(e) => e.currentTarget.select()}
          style={{ fontSize: 10, fontFamily: "var(--font-mono)", background: "var(--bg-1)", color: "var(--paper-0)", border: "1px solid var(--bg-2)", borderRadius: 4, padding: "4px 6px" }}
        />
      )}

      {status === "done" && (
        <div>
          <SectionLabel>Beats the alternatives? (§9 ★5)</SectionLabel>
          {!baselineComparison && (
            <button
              onClick={runBaselineComparison}
              disabled={comparingBaselines}
              style={{
                marginTop: 6,
                background: "none",
                border: "1px solid var(--bg-2)",
                borderRadius: 6,
                color: "var(--paper-0)",
                cursor: comparingBaselines ? "default" : "pointer",
                padding: "6px 10px",
                fontSize: 11,
              }}
            >
              {comparingBaselines ? "Comparing against 4 real baselines (~20s)..." : "Compare vs. baselines"}
            </button>
          )}
          {baselineError && <p style={{ fontSize: 11, color: "var(--warn)", marginTop: 4 }}>{baselineError}</p>}
          {baselineComparison && <BaselineComparisonChart result={baselineComparison} />}
        </div>
      )}

      {status === "done" && planId && version != null && (
        <CouncilMemoPanel planId={planId} version={version} />
      )}

      {sites.length > 0 && (
        <div>
          <SectionLabel>Ranked sites ({sites.length})</SectionLabel>
          {/* A real table, not just map pins -- every selected site is
              readable and sortable-by-eye without the map at all (§8.6:
              "every map layer has a table view... a peer view"). */}
          <div style={{ maxHeight: 260, overflowY: "auto", marginTop: 6 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: "var(--font-mono)" }}>
              <thead>
                <tr style={{ textAlign: "left", opacity: 0.6 }}>
                  <th style={{ padding: "2px 4px" }}>#</th>
                  <th style={{ padding: "2px 4px" }}>Type</th>
                  <th style={{ padding: "2px 4px", textAlign: "right" }}>Cost</th>
                  <th style={{ padding: "2px 4px", textAlign: "right" }}>+EWCB</th>
                </tr>
              </thead>
              <tbody>
                {sites.map((s) => (
                  <tr key={s.candidate_id} style={{ borderTop: "1px solid var(--bg-2)" }}>
                    <td style={{ padding: "2px 4px" }}>{s.rank}</td>
                    <td style={{ padding: "2px 4px" }}>{s.intervention_type}</td>
                    <td style={{ padding: "2px 4px", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {currency.format(s.cost_usd)}
                    </td>
                    <td style={{ padding: "2px 4px", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {number0.format(s.marginal_gain_ewcb)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </aside>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.5 }}>
      {children}
    </div>
  );
}
