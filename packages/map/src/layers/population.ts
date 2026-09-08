import { GeoJsonLayer } from "@deck.gl/layers";
import type { FeatureCollection } from "geojson";
import { scaleToStops } from "../colorScale";
import type { LayerRegistration } from "./registry";

// Sequential, low -> high: dark ground -> --cool -> --equity. Distinct from
// the heat-surface thermal ramp on purpose -- this is "how many people live
// here" (D1), not temperature, and using the same ramp as the heat surface
// would read as if the two were the same quantity.
const POPULATION_RAMP = ["#1a1f26", "#4cc9c0", "#f4b860"];
// From the real exported data: median ~2.8, p95 ~16, one capped outlier at
// 315 (a large apartment building against D1's own density cap -- see
// engine/equity/population.py). Domain set to p95-ish so the typical range
// of single-family/small-multifamily buildings is legible; the rare large
// building still reads as "the brightest colour available," not wrong.
const POPULATION_DOMAIN: [number, number] = [0, 20];

export const populationLayer: LayerRegistration<FeatureCollection> = {
  id: "population",
  label: "Dasymetric population (D1)",
  defaultVisible: false,
  loadData: async () => {
    const res = await fetch("/api/layers/population");
    if (!res.ok) throw new Error(`failed to load population layer: ${res.status}`);
    return res.json() as Promise<FeatureCollection>;
  },
  buildLayer: (data, visible) =>
    new GeoJsonLayer({
      id: "population",
      data,
      visible,
      filled: true,
      stroked: false,
      // Flat, not extruded: this shares its footprint geometry with the
      // buildings layer's own height-based extrusion (Phase 1/2) -- adding
      // a second, population-based extrusion on the same polygons would
      // z-fight against it when both are visible.
      getFillColor: (f) => {
        const pop = (f.properties?.population as number) ?? 0;
        const [r, g, b] = scaleToStops(pop, POPULATION_DOMAIN[0], POPULATION_DOMAIN[1], POPULATION_RAMP);
        return [r, g, b, 200];
      },
      pickable: true,
    }),
};
