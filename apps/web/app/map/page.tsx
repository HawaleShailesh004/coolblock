"use client";

import {
  CoolBlockMap,
  DEFAULT_LAYERS,
  DEFAULT_VIEW_STATE,
  type Layer,
  type LayerLoadStatus,
  type SelectedFeature,
  viewStateToSearchParam,
} from "@coolblock/map";
import type { FeatureCollection } from "geojson";
import { useCallback, useMemo, useRef, useState } from "react";
import type { Command } from "./CommandPalette";
import { useCommandPalette } from "./CommandPalette";
import { HviWeightsPanel } from "./HviWeightsPanel";
import { LayerTableView } from "./LayerTableView";
import { OptimizerPanel } from "./OptimizerPanel";

// Mirrors config/neighborhood.toml -- the scope lock. Presentation copy only;
// the engine reads the real file. See docs/adr/0002-scope-lock-and-build-posture.md.
const NEIGHBORHOOD = { name: "Edison-Eastlake", city: "Phoenix", state: "AZ" };

const PMTILES_URL =
  process.env.NEXT_PUBLIC_PMTILES_URL ?? "http://localhost:9000/coolblock-tiles/basemap.pmtiles";
const TITILER_URL = process.env.NEXT_PUBLIC_TITILER_URL ?? "http://localhost:8090";
const HEAT_SURFACE_COG_URL = "s3://coolblock-data/heat_surface_lst.tif";

// Not a deck.gl layer (see packages/map/src/heatSurface.ts) so it isn't part
// of DEFAULT_LAYERS, but it shares the same toggle UI and visibility map.
const HEAT_SURFACE_TOGGLE = {
  id: "heat-surface",
  label: "Heat surface (modeled -- see methodology)",
  defaultVisible: true,
};

export default function MapPage() {
  const [visibility, setVisibility] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(
      [...DEFAULT_LAYERS, HEAT_SURFACE_TOGGLE].map((l) => [l.id, l.defaultVisible]),
    ),
  );
  const [layerStatuses, setLayerStatuses] = useState<Record<string, LayerLoadStatus>>({});
  const [selected, setSelected] = useState<SelectedFeature | null>(null);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied">("idle");
  // Keyed by source rather than a single value: the live optimizer solve
  // and the HVI weight sliders each own an independent live layer, and
  // either, both, or neither can be active at once.
  const [liveLayersBySource, setLiveLayersBySource] = useState<Record<string, Layer | null>>({});
  const setOptimizerLiveLayer = useCallback(
    (layer: Layer | null) => setLiveLayersBySource((prev) => ({ ...prev, optimizer: layer })),
    [],
  );
  const setHviWeightsLiveLayer = useCallback(
    (layer: Layer | null) => setLiveLayersBySource((prev) => ({ ...prev, hviWeights: layer })),
    [],
  );
  const retryLayerRef = useRef<((layerId: string) => void) | null>(null);
  const handleRetryHandleReady = useCallback((retry: (layerId: string) => void) => {
    retryLayerRef.current = retry;
  }, []);
  const retryLayer = useCallback((layerId: string) => retryLayerRef.current?.(layerId), []);
  const [layerData, setLayerData] = useState<Record<string, FeatureCollection>>({});
  const handleLayerDataLoaded = useCallback((layerId: string, data: unknown) => {
    setLayerData((prev) => ({ ...prev, [layerId]: data as FeatureCollection }));
  }, []);
  const [tableViewLayerId, setTableViewLayerId] = useState<string | null>(null);
  // Stabilized so CoolBlockMap's liveLayers effect only refires when the
  // set of live layers actually changes, not on every unrelated page.tsx
  // re-render (a new array literal every render would otherwise look
  // like a change to the effect's dependency array).
  const liveLayers = useMemo(
    () => Object.values(liveLayersBySource).filter((l): l is Layer => l != null),
    [liveLayersBySource],
  );

  const commands: Command[] = useMemo(
    () => [
      ...[...DEFAULT_LAYERS, HEAT_SURFACE_TOGGLE].map((l) => ({
        id: `toggle-${l.id}`,
        label: `${visibility[l.id] ? "Hide" : "Show"} layer: ${l.label}`,
        run: () => setVisibility((v) => ({ ...v, [l.id]: !v[l.id] })),
      })),
      {
        id: "reset-view",
        label: "Reset camera to default view",
        run: () => {
          const url = new URL(window.location.href);
          url.searchParams.set("map", viewStateToSearchParam(DEFAULT_VIEW_STATE));
          window.location.href = url.toString();
        },
      },
      {
        id: "copy-link",
        label: "Copy shareable link to this view",
        run: () => {
          navigator.clipboard.writeText(window.location.href).then(() => {
            setCopyStatus("copied");
            setTimeout(() => setCopyStatus("idle"), 1500);
          });
        },
      },
    ],
    [visibility],
  );

  const { setOpen, palette } = useCommandPalette(commands);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateRows: "auto 1fr",
        height: "100vh",
        background: "var(--bg-0)",
        color: "var(--paper-0)",
        fontFamily: "var(--font-ui)",
      }}
    >
      <TopBar onOpenPalette={() => setOpen(true)} copyStatus={copyStatus} />
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr 280px 300px", overflow: "hidden" }}>
        <InspectorRail
          layers={[...DEFAULT_LAYERS, HEAT_SURFACE_TOGGLE]}
          visibility={visibility}
          onChange={setVisibility}
          statuses={layerStatuses}
          onRetry={retryLayer}
          onOpenTable={setTableViewLayerId}
          hviData={layerData["hvi"]}
          onHviLiveLayerChange={setHviWeightsLiveLayer}
        />
        <CoolBlockMap
          pmtilesUrl={PMTILES_URL}
          layers={DEFAULT_LAYERS}
          visibility={visibility}
          onLayerStatusChange={setLayerStatuses}
          onLayerDataLoaded={handleLayerDataLoaded}
          onRetryHandleReady={handleRetryHandleReady}
          onFeatureClick={setSelected}
          heatSurface={{ titilerBaseUrl: TITILER_URL, cogUrl: HEAT_SURFACE_COG_URL }}
          liveLayers={liveLayers}
        />
        <ContextPanel selected={selected} />
        <OptimizerPanel onLiveLayerChange={setOptimizerLiveLayer} />
      </div>
      {palette}
      {tableViewLayerId && layerData[tableViewLayerId] && (
        <LayerTableView
          label={[...DEFAULT_LAYERS, HEAT_SURFACE_TOGGLE].find((l) => l.id === tableViewLayerId)?.label ?? tableViewLayerId}
          data={layerData[tableViewLayerId]}
          onClose={() => setTableViewLayerId(null)}
        />
      )}
    </div>
  );
}

function TopBar({ onOpenPalette, copyStatus }: { onOpenPalette: () => void; copyStatus: "idle" | "copied" }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 14px",
        borderBottom: "1px solid var(--bg-2)",
        fontSize: 13,
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <span style={{ fontFamily: "var(--font-display)", fontSize: 16 }}>CoolBlock</span>
        <span style={{ opacity: 0.55, fontFamily: "var(--font-mono)", fontSize: 11 }}>
          {NEIGHBORHOOD.name} &middot; {NEIGHBORHOOD.city}, {NEIGHBORHOOD.state}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {copyStatus === "copied" && (
          <span style={{ color: "var(--ok)", fontSize: 12 }}>Link copied</span>
        )}
        <button
          onClick={onOpenPalette}
          style={{
            background: "var(--bg-1)",
            color: "var(--paper-0)",
            border: "1px solid var(--bg-2)",
            borderRadius: 6,
            padding: "5px 10px",
            fontSize: 12,
            fontFamily: "var(--font-mono)",
            cursor: "pointer",
          }}
        >
          &#8984;K Commands
        </button>
      </div>
    </div>
  );
}

interface LayerToggle {
  id: string;
  label: string;
  defaultVisible: boolean;
}

function InspectorRail({
  layers,
  visibility,
  onChange,
  statuses,
  onRetry,
  onOpenTable,
  hviData,
  onHviLiveLayerChange,
}: {
  layers: LayerToggle[];
  visibility: Record<string, boolean>;
  onChange: (v: Record<string, boolean>) => void;
  statuses: Record<string, LayerLoadStatus>;
  onRetry: (layerId: string) => void;
  onOpenTable: (layerId: string) => void;
  hviData: FeatureCollection | undefined;
  onHviLiveLayerChange: (layer: Layer | null) => void;
}) {
  return (
    <aside
      style={{
        borderRight: "1px solid var(--bg-2)",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 16,
        overflowY: "auto",
      }}
    >
      <section>
        <SectionLabel>Layers</SectionLabel>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
          {layers.map((layer) => {
            // The heat surface is a native MapLibre raster layer (see
            // CoolBlockMap.tsx), not one of CoolBlockMap's registry
            // layers -- it never reports a load status, and "feature
            // count" isn't a meaningful concept for a raster.
            const status = layer.id === "heat-surface" ? null : statuses[layer.id];
            return (
              <div key={layer.id}>
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                  <input
                    type="checkbox"
                    checked={visibility[layer.id] ?? layer.defaultVisible}
                    onChange={(e) => onChange({ ...visibility, [layer.id]: e.target.checked })}
                  />
                  <span style={{ flex: 1 }}>{layer.label}</span>
                  {status?.status === "error" ? (
                    <button
                      onClick={() => onRetry(layer.id)}
                      title={status.error}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--warn)",
                        cursor: "pointer",
                        padding: 0,
                        font: "inherit",
                        fontSize: 11,
                      }}
                    >
                      failed &middot; retry
                    </button>
                  ) : (
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, opacity: 0.5, fontVariantNumeric: "tabular-nums" }}>
                      {status === null ? "" : (status?.count ?? "...")}
                    </span>
                  )}
                </label>
                {status?.status === "loaded" && (
                  <button
                    onClick={() => onOpenTable(layer.id)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--cool)",
                      cursor: "pointer",
                      padding: "0 0 0 24px",
                      font: "inherit",
                      fontSize: 10,
                    }}
                  >
                    View as table
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </section>
      <HviWeightsPanel data={hviData} onLiveLayerChange={onHviLiveLayerChange} />
      <section>
        <SectionLabel>Neighborhood</SectionLabel>
        <p style={{ fontSize: 12, opacity: 0.7, lineHeight: 1.5, marginTop: 6 }}>
          Edison-Eastlake, Phoenix AZ. Locked scope -- see{" "}
          <code style={{ fontFamily: "var(--font-mono)" }}>config/neighborhood.toml</code>. Data ingested
          Phase 1: 2,844 buildings, 2,734 road segments, 2,956 parcels.
        </p>
      </section>
    </aside>
  );
}

function ContextPanel({ selected }: { selected: SelectedFeature | null }) {
  return (
    <aside
      style={{
        borderLeft: "1px solid var(--bg-2)",
        padding: 14,
        overflowY: "auto",
      }}
    >
      <SectionLabel>Inspector</SectionLabel>
      {!selected ? (
        <p style={{ fontSize: 12, opacity: 0.55, marginTop: 8, lineHeight: 1.5 }}>
          Click a building or parcel on the map to see its attributes here.
        </p>
      ) : (
        <div style={{ marginTop: 8, fontSize: 12, fontFamily: "var(--font-mono)" }}>
          <div style={{ opacity: 0.6, marginBottom: 6 }}>{selected.layerId}</div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              {Object.entries(selected.properties)
                .filter(([, v]) => v !== null && v !== undefined && v !== "")
                .map(([k, v]) => (
                  <tr key={k} style={{ borderTop: "1px solid var(--bg-2)" }}>
                    <td style={{ padding: "4px 4px 4px 0", opacity: 0.6, verticalAlign: "top" }}>{k}</td>
                    <td style={{ padding: "4px 0", wordBreak: "break-word" }}>{String(v)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </aside>
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
