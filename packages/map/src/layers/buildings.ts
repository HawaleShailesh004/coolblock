import { GeoJsonLayer } from "@deck.gl/layers";
import { colorTokens } from "@coolblock/ui";
import type { FeatureCollection } from "geojson";
import type { LayerRegistration } from "./registry";

// Semi-transparent, not solid: §9 ★1's own intent is "the surface glows
// beneath the 3D block" (CoolBlockMap.tsx's comment on the heat-surface
// layer) -- but at these values' original near-opaque range (190-255),
// ~2,844 densely-packed buildings viewed from the default pitched camera
// (pitch=50) visually occlude almost the entire heat surface underneath,
// a real, confirmed regression against that intent (screenshotted:
// buildings hidden shows the heat surface rendering correctly; buildings
// shown hides nearly all of it). Halved so the glow reads through the
// building volumes while still keeping the honesty-rail's own opacity
// *ordering* intact (measured > levels > estimated_default).
const HEIGHT_PROVENANCE_OPACITY: Record<string, number> = {
  measured: 130,
  levels: 115,
  estimated_default: 95, // visibly softer -- an estimate, not a measurement (honesty rail, §1.4)
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
