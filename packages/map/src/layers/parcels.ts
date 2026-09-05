import { GeoJsonLayer } from "@deck.gl/layers";
import type { FeatureCollection } from "geojson";
import type { LayerRegistration } from "./registry";

export const parcelsLayer: LayerRegistration<FeatureCollection> = {
  id: "parcels",
  label: "Parcel boundaries",
  defaultVisible: false,
  loadData: async () => {
    const res = await fetch("/api/layers/parcels");
    if (!res.ok) throw new Error(`failed to load parcels layer: ${res.status}`);
    return res.json() as Promise<FeatureCollection>;
  },
  buildLayer: (data, visible) =>
    new GeoJsonLayer({
      id: "parcels",
      data,
      visible,
      stroked: true,
      filled: false,
      getLineColor: [76, 201, 192, 90], // --cool, low alpha -- a reference layer, not a focal one
      lineWidthMinPixels: 0.5,
      pickable: true,
    }),
};
