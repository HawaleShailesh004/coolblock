/**
 * Linear-interpolated colour scales for data-driven deck.gl fill colours.
 * No charting/scale library is a dependency of this package (or of
 * packages/ui) -- this is a small, direct implementation rather than
 * pulling in d3-scale for two call sites (population density, HVI).
 */

type RGB = [number, number, number];

function hexToRgb(hex: string): RGB {
  const n = parseInt(hex.replace("#", ""), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Interpolates through an ordered list of hex stops at positions `t in [0, 1]`. */
export function interpolateHexStops(stops: string[], t: number): RGB {
  if (stops.length < 2) throw new Error("interpolateHexStops needs at least 2 stops");
  const clamped = Math.min(1, Math.max(0, t));
  const scaled = clamped * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(scaled));
  const localT = scaled - i;
  const [r0, g0, b0] = hexToRgb(stops[i] as string);
  const [r1, g1, b1] = hexToRgb(stops[i + 1] as string);
  return [Math.round(lerp(r0, r1, localT)), Math.round(lerp(g0, g1, localT)), Math.round(lerp(b0, b1, localT))];
}

/** Maps a value in `[domainMin, domainMax]` onto `[0, 1]` before interpolating -- clamps out-of-range values to the ends rather than extrapolating. */
export function scaleToStops(value: number, domainMin: number, domainMax: number, stops: string[]): RGB {
  if (domainMax === domainMin) return interpolateHexStops(stops, 0.5);
  return interpolateHexStops(stops, (value - domainMin) / (domainMax - domainMin));
}
