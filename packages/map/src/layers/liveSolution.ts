import type { Layer } from "@deck.gl/core";
import { GeoJsonLayer } from "@deck.gl/layers";
import type { Feature, FeatureCollection, Geometry } from "geojson";

/**
 * Phase 8 -- the live counterpart to `optimizerSelection.ts`'s static,
 * pre-baked demo layer: sites landing one at a time from a real SSE
 * solve (`apps/web/lib/sse.ts` + `apps/web/app/map/OptimizerPanel.tsx`),
 * not a single fetch of a pre-solved file. Same highlight colour as the
 * static layer -- both mean the same thing ("this is what CoolBlock
 * picked"), just from a live run instead of a demo-budget one.
 */
export interface LiveSolutionSite {
  rank: number;
  candidateId: string;
  interventionType: string;
  costUsd: number;
  marginalGainEwcb: number;
  cumulativeEwcb: number;
  cumulativeCostUsd: number;
  geometry: Geometry;
  properties: Record<string, unknown>;
}

const LIVE_SOLUTION_COLOR: [number, number, number] = [255, 255, 255]; // matches optimizerSelection.ts's SELECTED_COLOR

export function buildLiveSolutionLayer(sites: LiveSolutionSite[]): Layer {
  const data: FeatureCollection = {
    type: "FeatureCollection",
    features: sites.map(
      (s): Feature => ({
        type: "Feature",
        geometry: s.geometry,
        properties: {
          ...s.properties,
          rank: s.rank,
          candidate_id: s.candidateId,
          intervention_type: s.interventionType,
          cost_usd: s.costUsd,
          marginal_gain_ewcb: s.marginalGainEwcb,
          cumulative_ewcb: s.cumulativeEwcb,
          cumulative_cost_usd: s.cumulativeCostUsd,
        },
      }),
    ),
  };

  return new GeoJsonLayer({
    id: "live-optimizer-solution",
    data,
    filled: true,
    stroked: true,
    getFillColor: [...LIVE_SOLUTION_COLOR, 70],
    getLineColor: [...LIVE_SOLUTION_COLOR, 255],
    lineWidthMinPixels: 3,
    pickable: true,
  });
}
