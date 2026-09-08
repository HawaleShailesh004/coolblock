import { buildingsLayer } from "./buildings";
import { candidatesLayer } from "./candidates";
import { hviLayer } from "./hvi";
import { optimizerSelectionLayer } from "./optimizerSelection";
import { parcelsLayer } from "./parcels";
import { populationLayer } from "./population";
import { createLayerRegistry } from "./registry";
import { roadsLayer } from "./roads";

// Registration order is z-order (first = bottom). Add a Phase 5+ layer here.
// hvi and population are choropleths -- kept low in the stack so a toggled
// intervention/selection layer on top of them stays legible.
// optimizerSelectionLayer is last -- its highlight outline needs to stay
// visible on top of the base candidates layer, not be obscured by it.
export const DEFAULT_LAYERS = createLayerRegistry([
  roadsLayer,
  parcelsLayer,
  hviLayer,
  populationLayer,
  candidatesLayer,
  buildingsLayer,
  optimizerSelectionLayer,
]);

export { buildingsLayer, candidatesLayer, hviLayer, optimizerSelectionLayer, parcelsLayer, populationLayer, roadsLayer };
export { INTERVENTION_COLOR } from "./candidates";
export { buildLiveSolutionLayer } from "./liveSolution";
export type { LiveSolutionSite } from "./liveSolution";
export { createLayerRegistry } from "./registry";
export type { LayerRegistration } from "./registry";
