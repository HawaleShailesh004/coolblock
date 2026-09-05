import { buildingsLayer } from "./buildings";
import { candidatesLayer } from "./candidates";
import { parcelsLayer } from "./parcels";
import { createLayerRegistry } from "./registry";
import { roadsLayer } from "./roads";

// Registration order is z-order (first = bottom). Add a Phase 5+ layer here.
export const DEFAULT_LAYERS = createLayerRegistry([roadsLayer, parcelsLayer, candidatesLayer, buildingsLayer]);

export { buildingsLayer, candidatesLayer, parcelsLayer, roadsLayer };
export { INTERVENTION_COLOR } from "./candidates";
export { createLayerRegistry } from "./registry";
export type { LayerRegistration } from "./registry";
