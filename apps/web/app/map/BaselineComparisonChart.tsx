"use client";

/**
 * Phase 8/9, §9 ★5: "we beat the alternatives." Five real strategies,
 * same budget, same neighborhood, scored by the same EWCB yardstick --
 * "this screen is the product's argument for its own existence." A plain
 * horizontal bar chart, not a placeholder: every bar's width is exactly
 * proportional to a real number from `apps/api`'s `/baselines` endpoint
 * (`engine.optimize.baselines.run_all_baselines`).
 */

const STRATEGY_LABELS: Record<string, string> = {
  coolblock: "CoolBlock (CELF)",
  tes_score_only: "Tree Equity Score only",
  worst_first: "Worst-first (hottest first)",
  spread_evenly: "Spread evenly",
  squeaky_wheel: "Squeaky wheel (status quo)",
};

const number0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export function BaselineComparisonChart({ result }: { result: Record<string, number> }) {
  const maxValue = Math.max(...Object.values(result), 1);
  const rows = Object.entries(result).sort(([, a], [, b]) => b - a);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }} role="table" aria-label="Strategy comparison, equity-weighted cooling benefit">
      {rows.map(([key, value]) => {
        const isCoolBlock = key === "coolblock";
        const widthPct = Math.max(2, (value / maxValue) * 100);
        return (
          <div key={key} role="row" style={{ fontSize: 11 }}>
            <div role="cell" style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
              <span style={{ opacity: isCoolBlock ? 1 : 0.75, fontWeight: isCoolBlock ? 600 : 400 }}>
                {STRATEGY_LABELS[key] ?? key}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums" }}>
                {number0.format(value)}
              </span>
            </div>
            <div style={{ background: "var(--bg-2)", borderRadius: 3, height: 8 }}>
              <div
                role="cell"
                aria-label={`${STRATEGY_LABELS[key] ?? key}: ${number0.format(value)} equity-weighted person-degree-hours`}
                style={{
                  width: `${widthPct}%`,
                  height: "100%",
                  borderRadius: 3,
                  background: isCoolBlock ? "var(--cool)" : "var(--bg-2)",
                  border: isCoolBlock ? "none" : "1px solid rgba(255,255,255,0.25)",
                }}
              />
            </div>
          </div>
        );
      })}
      <p style={{ fontSize: 10, opacity: 0.5, marginTop: 4 }}>
        Equity-weighted person-degree-hours (D4), same budget, same candidate universe.
      </p>
    </div>
  );
}
