"use client";

import type { Feature, FeatureCollection } from "geojson";
import { useMemo } from "react";

/**
 * Phase 8 (§8.6): "Every map layer has a table view. A screen reader user
 * can read the ranked plan as a sortable table with all the same
 * numbers. This is not a fallback, it is a peer view -- and it doubles
 * as the export preview." This is that view, for any layer, not just the
 * live optimizer's ranked-sites table (`OptimizerPanel.tsx`) -- reusing
 * the same "one row per feature, one column per property" shape.
 *
 * No virtualization: at this neighborhood's real scale (a few thousand
 * features per layer, per `docs/adr/0017-*.md`'s PMTiles deferral), a
 * plain scrollable `<table>` renders acceptably. Disclosed here rather
 * than silently degrading on a future, much larger layer.
 */
export function LayerTableView({
  label,
  data,
  onClose,
}: {
  label: string;
  data: FeatureCollection;
  onClose: () => void;
}) {
  const { columns, rows } = useMemo(() => {
    const keys = new Set<string>();
    for (const feature of data.features) {
      for (const [k, v] of Object.entries(feature.properties ?? {})) {
        if (v !== null && v !== undefined && v !== "") keys.add(k);
      }
    }
    const columns = [...keys].sort();
    const rows = data.features.map((f: Feature) => f.properties ?? {});
    return { columns, rows };
  }, [data]);

  return (
    <div
      role="dialog"
      aria-label={`${label} -- table view`}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(10, 12, 15, 0.92)",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        padding: 20,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--paper-0)" }}>
          {label} <span style={{ opacity: 0.5 }}>&middot; {rows.length} rows</span>
        </div>
        <button
          onClick={onClose}
          autoFocus
          style={{
            background: "var(--bg-1)",
            color: "var(--paper-0)",
            border: "1px solid var(--bg-2)",
            borderRadius: 6,
            padding: "5px 10px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          Close
        </button>
      </div>
      <div style={{ flex: 1, overflow: "auto", border: "1px solid var(--bg-2)", borderRadius: 6 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: "var(--font-mono)" }}>
          <thead style={{ position: "sticky", top: 0, background: "var(--bg-1)" }}>
            <tr>
              {columns.map((col) => (
                <th key={col} style={{ textAlign: "left", padding: "6px 8px", whiteSpace: "nowrap", color: "var(--paper-0)" }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              // Rows have no stable id in general GeoJSON -- index keys are
              // safe here since this list is never reordered or filtered
              // in place, only replaced wholesale when the layer reloads.
              <tr key={i} style={{ borderTop: "1px solid var(--bg-2)", color: "var(--paper-0)" }}>
                {columns.map((col) => (
                  <td key={col} style={{ padding: "4px 8px", whiteSpace: "nowrap" }}>
                    {row[col] === null || row[col] === undefined ? "" : String(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
