import { Protocol } from "pmtiles";
import type maplibregl from "maplibre-gl";

let registered = false;

/** Registers the pmtiles:// protocol with MapLibre. Idempotent -- safe to
 * call from every mount without leaking duplicate protocol handlers. */
export function registerPmtilesProtocol(maplibre: typeof maplibregl): void {
  if (registered) return;
  const protocol = new Protocol();
  maplibre.addProtocol("pmtiles", protocol.tile);
  registered = true;
}
