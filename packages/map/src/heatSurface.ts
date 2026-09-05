/**
 * The Phase 3 heat surface, served as raster tiles via TiTiler from the COG
 * uploaded by scripts/export_heat_surface.py (§10 Phase 3: "Export to COG
 * -> R2 -> TiTiler; a HeatSurfaceLayer in packages/map").
 *
 * Labeled "modeled surface temperature" everywhere, not "predicted
 * cooling" -- the A3 validation gate passed 2 of 3 checks (see
 * docs/METHODOLOGY.md, docs/adr/0004-*.md), and §1.4's honesty rail means
 * this layer makes no claim about what an intervention would achieve.
 * That claim doesn't exist until Phase 5/6 anyway; this is the raw
 * (downscaled) observed-temperature surface.
 */

// Real min/max from the current COG (scripts/export_heat_surface.py output),
// used to anchor the color ramp. Re-check after re-running the export if the
// underlying data changes meaningfully.
export const HEAT_SURFACE_RESCALE: [number, number] = [51, 59];
export const HEAT_SURFACE_COLORMAP = "inferno";

export function buildHeatSurfaceTileUrl(titilerBaseUrl: string, cogUrl: string): string {
  const params = new URLSearchParams({
    url: cogUrl,
    rescale: HEAT_SURFACE_RESCALE.join(","),
    colormap_name: HEAT_SURFACE_COLORMAP,
  });
  return `${titilerBaseUrl}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?${params.toString()}`;
}
