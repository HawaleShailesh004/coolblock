export interface MapViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
}

// Edison-Eastlake centroid, roughly overhead, angled for the 3D extrusion (§9 ★1).
export const DEFAULT_VIEW_STATE: MapViewState = {
  longitude: -112.0555,
  latitude: 33.455,
  zoom: 15.5,
  pitch: 50,
  bearing: -17,
};

const PARAM = "map"; // ?map=lng,lat,zoom,pitch,bearing
const PRECISION = { lnglat: 5, zoom: 2, angle: 1 } as const;

/** Deep-linkable map state (Phase 2 DoD: "shareable by URL"). */
export function viewStateToSearchParam(v: MapViewState): string {
  return [
    v.longitude.toFixed(PRECISION.lnglat),
    v.latitude.toFixed(PRECISION.lnglat),
    v.zoom.toFixed(PRECISION.zoom),
    v.pitch.toFixed(PRECISION.angle),
    v.bearing.toFixed(PRECISION.angle),
  ].join(",");
}

export function parseViewStateFromSearch(search: string): MapViewState | null {
  const raw = new URLSearchParams(search).get(PARAM);
  if (!raw) return null;
  const parts = raw.split(",").map(Number);
  if (parts.length !== 5 || parts.some((n) => Number.isNaN(n))) return null;
  const [longitude, latitude, zoom, pitch, bearing] = parts as [number, number, number, number, number];
  return { longitude, latitude, zoom, pitch, bearing };
}

export function writeViewStateToUrl(v: MapViewState): void {
  const url = new URL(window.location.href);
  url.searchParams.set(PARAM, viewStateToSearchParam(v));
  window.history.replaceState(null, "", url);
}

export function readViewStateFromUrl(): MapViewState {
  return parseViewStateFromSearch(window.location.search) ?? DEFAULT_VIEW_STATE;
}
