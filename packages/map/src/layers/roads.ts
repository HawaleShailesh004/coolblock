import { GeoJsonLayer } from "@deck.gl/layers";
import type { FeatureCollection } from "geojson";
import type { LayerRegistration } from "./registry";

export const roadsLayer: LayerRegistration<FeatureCollection> = {
  id: "roads",
  label: "Roads",
  defaultVisible: true,
  loadData: async () => {
    const res = await fetch("/api/layers/roads");
    if (!res.ok) throw new Error(`failed to load roads layer: ${res.status}`);
    return res.json() as Promise<FeatureCollection>;
  },
  buildLayer: (data, visible) =>
    new GeoJsonLayer({
      id: "roads",
      data,
      visible,
      stroked: true,
      filled: false,
      getLineColor: [255, 255, 255, 110],
      lineWidthMinPixels: 1,
      pickable: false,
    }),
};
