import type { Layer } from "@deck.gl/core";

/**
 * The layer-registry architecture (§10 Phase 2): every later layer (heat
 * surface, plantable space, candidates, selected sites, HVI choropleth --
 * §8.3 Phase 8) is a plug-in registered here, not a change to the map
 * component itself. A registry entry owns its own data fetch and its own
 * deck.gl layer construction; CoolBlockMap just renders whatever the
 * registry currently holds.
 */
export interface LayerRegistration<TData = unknown> {
  id: string;
  label: string;
  defaultVisible: boolean;
  /** Fetches this layer's data. Called once; the map component owns caching. */
  loadData: () => Promise<TData>;
  /** Builds the deck.gl layer instance from loaded data and current visibility. */
  buildLayer: (data: TData, visible: boolean) => Layer;
}

// Registrations are heterogeneous by nature (a future raster layer's TData
// won't match a vector layer's) -- the registry container erases to `any`
// at the array boundary the same way any plugin-registry type does; each
// registration is still fully typed where it's *defined*.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function createLayerRegistry(registrations: LayerRegistration<any>[]): LayerRegistration<any>[] {
  const ids = new Set<string>();
  for (const r of registrations) {
    if (ids.has(r.id)) throw new Error(`duplicate layer id in registry: ${r.id}`);
    ids.add(r.id);
  }
  return registrations;
}
