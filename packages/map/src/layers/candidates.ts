import { GeoJsonLayer } from "@deck.gl/layers";
import type { FeatureCollection } from "geojson";
import type { LayerRegistration } from "./registry";

// One colour per intervention type -- distinct from the thermal ramp and
// from --cool/--equity, which already mean something else in this product.
const INTERVENTION_COLOR: Record<string, [number, number, number]> = {
  street_tree: [107, 203, 119], // --ok
  park_lot_tree_cluster: [76, 201, 192], // --cool
  shade_structure: [244, 184, 96], // --equity
  cool_pavement: [232, 106, 92], // --warn
  cool_roof: [163, 177, 198], // reflective/silver, distinct from every other token -- Phase 5 albedo candidates
};
const DEFAULT_COLOR: [number, number, number] = [150, 150, 150];

export const candidatesLayer: LayerRegistration<FeatureCollection> = {
  id: "candidates",
  label: "Intervention candidates (Phase 4/5)",
  defaultVisible: false,
  loadData: async () => {
    const res = await fetch("/api/layers/candidates");
    if (!res.ok) throw new Error(`failed to load candidates layer: ${res.status}`);
    return res.json() as Promise<FeatureCollection>;
  },
  buildLayer: (data, visible) =>
    new GeoJsonLayer({
      id: "candidates",
      data,
      visible,
      filled: true,
      stroked: true,
      getFillColor: (f) => {
        const type = (f.properties?.intervention_type as string) ?? "";
        const [r, g, b] = INTERVENTION_COLOR[type] ?? DEFAULT_COLOR;
        return [r, g, b, 130];
      },
      getLineColor: (f) => {
        const type = (f.properties?.intervention_type as string) ?? "";
        const [r, g, b] = INTERVENTION_COLOR[type] ?? DEFAULT_COLOR;
        return [r, g, b, 220];
      },
      lineWidthMinPixels: 1,
      pickable: true,
    }),
};

// Re-exported so the app shell can build a legend without duplicating the
// colour mapping.
export { INTERVENTION_COLOR };
