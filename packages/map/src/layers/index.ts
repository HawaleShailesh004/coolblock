import { buildingsLayer } from "./buildings";
import { candidatesLayer } from "./candidates";
import { optimizerSelectionLayer } from "./optimizerSelection";
import { parcelsLayer } from "./parcels";
import { createLayerRegistry } from "./registry";
import { roadsLayer } from "./roads";

// Registration order is z-order (first = bottom). Add a Phase 5+ layer here.
// optimizerSelectionLayer is last -- its highlight outline needs to stay
// visible on top of the base candidates layer, not be obscured by it.
export const DEFAULT_LAYERS = createLayerRegistry([
  roadsLayer,
  parcelsLayer,
  candidatesLayer,
  buildingsLayer,
  optimizerSelectionLayer,
]);

export { buildingsLayer, candidatesLayer, optimizerSelectionLayer, parcelsLayer, roadsLayer };
export { INTERVENTION_COLOR } from "./candidates";
export { createLayerRegistry } from "./registry";
export type { LayerRegistration } from "./registry";
