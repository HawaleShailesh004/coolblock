import { colorTokens } from "@coolblock/ui";
import { layersWithPartialCustomTheme } from "protomaps-themes-base";
import type { StyleSpecification } from "maplibre-gl";

const BASEMAP_SOURCE = "basemap";

/**
 * The "instrument" basemap style (§8.1, §8.2): near-black ground so the
 * thermal ramp stays the only strong colour on screen. Built on Protomaps'
 * "black" theme, hand-tuned with our own tokens rather than used as-is --
 * water reads as --cool (the product's "cooling delivered" colour, reused
 * here so the whole app agrees on what that hue means) and buildings sit a
 * step above the canvas on --bg-2.
 *
 * `glyphs`/`sprite` point at the neighborhood's self-hosted MinIO copy
 * (`assetsBaseUrl`, `scripts/build_map_assets.sh`) rather than
 * protomaps.github.io directly -- a real Phase 13 hardening gap
 * (docs/adr/0022-*.md): "offline demo mode... verified with the network
 * throttled to zero" would otherwise silently drop every map label and
 * icon the moment the internet is off, even though the basemap tiles
 * themselves were already self-hosted (`scripts/build_basemap.sh`).
 */
export function buildBasemapStyle(pmtilesUrl: string, assetsBaseUrl: string): StyleSpecification {
  const layers = layersWithPartialCustomTheme(BASEMAP_SOURCE, "black", {
    background: colorTokens.bg0,
    earth: colorTokens.bg0,
    water: colorTokens.cool,
    buildings: colorTokens.bg2,
    park_a: colorTokens.bg1,
    park_b: colorTokens.bg1,
  });

  return {
    version: 8,
    glyphs: `${assetsBaseUrl}/glyphs/{fontstack}/{range}.pbf`,
    sprite: `${assetsBaseUrl}/sprites/black`,
    sources: {
      [BASEMAP_SOURCE]: {
        type: "vector",
        url: `pmtiles://${pmtilesUrl}`,
        attribution:
          '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors, ' +
          '<a href="https://protomaps.com">Protomaps</a>',
      },
    },
    layers,
  };
}
