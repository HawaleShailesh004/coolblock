import { GeoJsonLayer } from "@deck.gl/layers";
import type { FeatureCollection } from "geojson";
import { scaleToStops } from "../colorScale";
import type { LayerRegistration } from "./registry";

// Diverging around 0: --cool (below-average vulnerability) -> dark ground
// (neutral) -> --warn (above-average vulnerability). HVI (D2) is a mean of
// six z-scores computed *within this neighborhood's own 23 block groups*
// (engine/equity/hvi.py) -- 0 is this neighborhood's own average, not a
// citywide or absolute baseline, which is why the scale is centered on the
// data's own zero rather than an external reference range.
const HVI_RAMP = ["#4cc9c0", "#1a1f26", "#e86a5c"];
// The real exported data's range (18 block groups, this neighborhood only)
// is [-0.86, +1.35] -- domain rounded outward to [-1.5, 1.5] so the most
// extreme block group doesn't sit exactly at the ramp's clipped end.
const HVI_DOMAIN: [number, number] = [-1.5, 1.5];

export const hviLayer: LayerRegistration<FeatureCollection> = {
  id: "hvi",
  label: "Heat Vulnerability Index (D2)",
  defaultVisible: false,
  loadData: async () => {
    const res = await fetch("/api/layers/hvi");
    if (!res.ok) throw new Error(`failed to load HVI layer: ${res.status}`);
    return res.json() as Promise<FeatureCollection>;
  },
  buildLayer: (data, visible) =>
    new GeoJsonLayer({
      id: "hvi",
      data,
      visible,
      filled: true,
      stroked: true,
      getFillColor: (f) => {
        const hvi = (f.properties?.hvi as number) ?? 0;
        const [r, g, b] = scaleToStops(hvi, HVI_DOMAIN[0], HVI_DOMAIN[1], HVI_RAMP);
        return [r, g, b, 110];
      },
      getLineColor: [200, 200, 200, 160],
      lineWidthMinPixels: 1,
      pickable: true,
    }),
};
