"use client";

import { buildHviChoroplethLayer, type Layer } from "@coolblock/map";
import type { Feature, FeatureCollection } from "geojson";
import { useEffect, useMemo, useState } from "react";

/**
 * Phase 8, §6.4 D2: "Weights are exposed in the UI as sliders (a planner
 * can and should argue with them), defaulting to equal weight with a
 * documented sensitivity analysis." This is that control.
 *
 * Recomputes the Heat Vulnerability Index **client-side**, from the six
 * real per-indicator z-scores `scripts/export_map_layers.py`'s
 * `export_hvi_choropleth()` already exports alongside the default,
 * equal-weight `hvi` value -- not a second backend call. The math
 * mirrors `engine.equity.hvi.compute_hvi()` exactly:
 * `hvi = mean(z_indicator * weight_indicator)` across all six indicators
 * (a fixed divide-by-6, not divided by the sum of the weights -- matching
 * `df[z_cols].mean(axis=1)` after each column is already multiplied by
 * its own weight).
 */

const INDICATORS = [
  { key: "svi", label: "Social Vulnerability Index" },
  { key: "pct_age65_plus", label: "% age 65+" },
  { key: "pct_age_under5", label: "% age <5" },
  { key: "asthma_chd_prevalence", label: "Asthma + CHD prevalence" },
  { key: "pct_renter", label: "% renter" },
  { key: "pct_no_vehicle", label: "% no vehicle" },
] as const;

type IndicatorKey = (typeof INDICATORS)[number]["key"];

function defaultWeights(): Record<IndicatorKey, number> {
  return Object.fromEntries(INDICATORS.map((i) => [i.key, 1])) as Record<IndicatorKey, number>;
}

function recomputeHvi(data: FeatureCollection, weights: Record<IndicatorKey, number>): FeatureCollection {
  return {
    ...data,
    features: data.features.map((f: Feature): Feature => {
      const props = f.properties ?? {};
      const sum = INDICATORS.reduce((acc, { key }) => {
        const z = props[`z_${key}`];
        return acc + (typeof z === "number" ? z * weights[key] : 0);
      }, 0);
      return { ...f, properties: { ...props, hvi: sum / INDICATORS.length } };
    }),
  };
}

export function HviWeightsPanel({
  data,
  onLiveLayerChange,
}: {
  data: FeatureCollection | undefined;
  onLiveLayerChange: (layer: Layer | null) => void;
}) {
  const [weights, setWeights] = useState<Record<IndicatorKey, number>>(defaultWeights);
  const [enabled, setEnabled] = useState(false);
  const isDefault = INDICATORS.every((i) => weights[i.key] === 1);

  const recomputed = useMemo(() => (data ? recomputeHvi(data, weights) : null), [data, weights]);

  useEffect(() => {
    onLiveLayerChange(enabled && recomputed ? buildHviChoroplethLayer("hvi-weighted-live", recomputed) : null);
    // onLiveLayerChange is a stable setter from the parent; only enabled/recomputed should retrigger this.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, recomputed]);

  return (
    <section>
      <SectionLabel>Equity weights (HVI, D2)</SectionLabel>
      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, marginTop: 6 }}>
        <input
          type="checkbox"
          checked={enabled}
          disabled={!data}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        <span style={{ flex: 1 }}>Show weighted HVI on map</span>
      </label>
      {!data && (
        <p style={{ fontSize: 11, opacity: 0.5, marginTop: 4 }}>Loading the HVI layer&apos;s data first...</p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
        {INDICATORS.map(({ key, label }) => (
          <label key={key} style={{ display: "flex", flexDirection: "column", gap: 2, fontSize: 11 }}>
            <span style={{ display: "flex", justifyContent: "space-between", opacity: 0.75 }}>
              <span>{label}</span>
              <span style={{ fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums" }}>
                {weights[key].toFixed(1)}
              </span>
            </span>
            <input
              type="range"
              min={0}
              max={2}
              step={0.1}
              value={weights[key]}
              onChange={(e) => setWeights((w) => ({ ...w, [key]: Number(e.target.value) }))}
            />
          </label>
        ))}
      </div>
      {!isDefault && (
        <button
          onClick={() => setWeights(defaultWeights())}
          style={{
            marginTop: 8,
            background: "none",
            border: "none",
            color: "var(--cool)",
            cursor: "pointer",
            padding: 0,
            font: "inherit",
            fontSize: 11,
          }}
        >
          Reset to equal weights
        </button>
      )}
    </section>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 10,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        opacity: 0.5,
      }}
    >
      {children}
    </div>
  );
}
