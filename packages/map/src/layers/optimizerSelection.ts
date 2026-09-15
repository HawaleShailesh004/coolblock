import { GeoJsonLayer } from "@deck.gl/layers";
import type { FeatureCollection } from "geojson";
import type { LayerRegistration } from "./registry";

// A single, unambiguous highlight colour distinct from every intervention-type
// colour in candidates.ts and from --cool/--equity/--warn/--ok -- the point of
// this layer is "these specific sites are what CoolBlock actually picked,"
// not another category to disambiguate against the base candidates layer.
const SELECTED_COLOR: [number, number, number] = [255, 255, 255]; // paper1 -- reads as "selected" against every other layer's darker fills

export const optimizerSelectionLayer: LayerRegistration<FeatureCollection> = {
  id: "optimizer-selection",
  label: "CoolBlock's plan (trees on public land, $50k)",
  defaultVisible: false,
  loadData: async () => {
    const res = await fetch("/api/layers/optimizer_selection");
    if (!res.ok) throw new Error(`failed to load optimizer_selection layer: ${res.status}`);
    return res.json() as Promise<FeatureCollection>;
  },
  buildLayer: (data, visible) =>
    new GeoJsonLayer({
      id: "optimizer-selection",
      data,
      visible,
      filled: true,
      stroked: true,
      getFillColor: [...SELECTED_COLOR, 60],
      getLineColor: [...SELECTED_COLOR, 255],
      lineWidthMinPixels: 3,
      pickable: true,
    }),
};
