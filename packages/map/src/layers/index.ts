import { buildingsLayer } from "./buildings";
import { parcelsLayer } from "./parcels";
import { createLayerRegistry } from "./registry";
import { roadsLayer } from "./roads";

// Registration order is z-order (first = bottom). Add a Phase 4+ layer here.
export const DEFAULT_LAYERS = createLayerRegistry([roadsLayer, parcelsLayer, buildingsLayer]);

export { buildingsLayer, parcelsLayer, roadsLayer };
export { createLayerRegistry } from "./registry";
export type { LayerRegistration } from "./registry";
