"use client";

import type { ScenarioVersionDetail } from "@coolblock/schema";
import { use, useEffect, useState } from "react";
import { ApiError, getSharedScenario } from "../../../lib/api";

/**
 * §1.2's "a public read-only scenario link" -- the read-only counterpart
 * to `OptimizerPanel`'s "Share link" button. The backend's
 * `GET /share/{token}` (apps/api/src/coolblock_api/routers/share.py) was
 * already built and needs no auth by design, but this page did not exist
 * until now -- a real gap found while writing this project's first E2E
 * tests: the share button generated a URL with nowhere to land.
 *
 * A generated OG image for link previews (§9.7) is a disclosed remaining
 * gap, not built here.
 */
const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const number0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; scenario: ScenarioVersionDetail };

export default function SharedScenarioPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    getSharedScenario(token)
      .then((scenario) => {
        if (!cancelled) setState({ status: "loaded", scenario });
      })
      .catch((err) => {
        if (cancelled) return;
        const message =
          err instanceof ApiError && err.status === 404
            ? "This share link doesn't exist, or has been revoked."
            : err instanceof Error
              ? err.message
              : "Failed to load this shared plan.";
        setState({ status: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--bg-0)",
        color: "var(--paper-0)",
        padding: "32px 20px",
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div style={{ width: "100%", maxWidth: 720 }}>
        <p style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.5 }}>
          CoolBlock &middot; shared plan (read-only)
        </p>

        {state.status === "loading" && <p style={{ marginTop: 16, fontSize: 14, opacity: 0.7 }}>Loading&hellip;</p>}

        {state.status === "error" && (
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 16, color: "var(--warn)" }}>{state.message}</p>
            <a href="/map" style={{ fontSize: 13, color: "var(--cool)" }}>
              Go to CoolBlock &rarr;
            </a>
          </div>
        )}

        {state.status === "loaded" && <SharedScenario scenario={state.scenario} />}
      </div>
    </main>
  );
}

function SharedScenario({ scenario }: { scenario: ScenarioVersionDetail }) {
  return (
    <>
      <h1 style={{ marginTop: 8, fontFamily: "var(--font-display)", fontSize: 28 }}>
        Scenario v{scenario.version_number}
      </h1>
      <p style={{ marginTop: 8, fontSize: 13, opacity: 0.8 }}>
        {scenario.sites.length} sites &middot; {currency.format(scenario.cost_usd ?? 0)} &middot;{" "}
        {number0.format(scenario.objective_value_ewcb ?? 0)} EWCB &middot; solver: {scenario.solver ?? "unknown"}
      </p>

      <div style={{ marginTop: 20 }}>
        <p style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.5 }}>
          Ranked sites ({scenario.sites.length})
        </p>
        <div style={{ maxHeight: 480, overflowY: "auto", marginTop: 8, border: "1px solid var(--bg-2)", borderRadius: 6 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "var(--font-mono)" }}>
            <thead>
              <tr style={{ textAlign: "left", opacity: 0.6 }}>
                <th style={{ padding: "6px 8px" }}>#</th>
                <th style={{ padding: "6px 8px" }}>Type</th>
                <th style={{ padding: "6px 8px", textAlign: "right" }}>Cost</th>
                <th style={{ padding: "6px 8px", textAlign: "right" }}>+EWCB</th>
              </tr>
            </thead>
            <tbody>
              {scenario.sites.map((s) => (
                <tr key={s.candidate_id} style={{ borderTop: "1px solid var(--bg-2)" }}>
                  <td style={{ padding: "6px 8px" }}>{s.rank}</td>
                  <td style={{ padding: "6px 8px" }}>{s.intervention_type}</td>
                  <td style={{ padding: "6px 8px", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                    {currency.format(s.cost_usd)}
                  </td>
                  <td style={{ padding: "6px 8px", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                    {number0.format(s.marginal_gain_ewcb)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p style={{ marginTop: 24, fontSize: 11, opacity: 0.5 }}>
        Shared read-only from CoolBlock &middot; <a href="/map" style={{ color: "var(--cool)" }}>open the live product &rarr;</a>
      </p>
    </>
  );
}
