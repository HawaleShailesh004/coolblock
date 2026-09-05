import { GeoJsonLayer } from "@deck.gl/layers";
import { colorTokens } from "@coolblock/ui";
import type { FeatureCollection } from "geojson";
import type { LayerRegistration } from "./registry";

const HEIGHT_PROVENANCE_OPACITY: Record<string, number> = {
  measured: 255,
  levels: 235,
  estimated_default: 190, // visibly softer -- an estimate, not a measurement (honesty rail, §1.4)
};

function hexToRgb(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const BUILDING_RGB = hexToRgb(colorTokens.bg2);

export const buildingsLayer: LayerRegistration<FeatureCollection> = {
  id: "buildings",
  label: "Buildings (extruded)",
  defaultVisible: true,
  loadData: async () => {
    const res = await fetch("/api/layers/buildings");
    if (!res.ok) throw new Error(`failed to load buildings layer: ${res.status}`);
    return res.json() as Promise<FeatureCollection>;
  },
  buildLayer: (data, visible) =>
    new GeoJsonLayer({
      id: "buildings",
      data,
      visible,
      extruded: true,
      wireframe: true,
      filled: true,
      getElevation: (f) => (f.properties?.height_m as number) ?? 5,
      getFillColor: (f) => {
        const provenance = (f.properties?.height_provenance as string) ?? "estimated_default";
        const alpha = HEIGHT_PROVENANCE_OPACITY[provenance] ?? 190;
        return [...BUILDING_RGB, alpha];
      },
      getLineColor: [0, 0, 0, 80],
      lineWidthMinPixels: 1,
      pickable: true,
    }),
};
