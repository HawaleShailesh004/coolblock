"use client";

import { MapboxOverlay } from "@deck.gl/mapbox";
import type { PickingInfo } from "@deck.gl/core";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import { buildBasemapStyle } from "./basemapStyle";
import { buildHeatSurfaceTileUrl } from "./heatSurface";
import type { LayerRegistration } from "./layers/registry";
import { registerPmtilesProtocol } from "./pmtiles";
import { readViewStateFromUrl, writeViewStateToUrl } from "./viewState";

export interface SelectedFeature {
  layerId: string;
  properties: Record<string, unknown>;
}

const HEAT_SOURCE_ID = "heat-surface-src";
const HEAT_LAYER_ID = "heat-surface-layer";

export interface CoolBlockMapProps {
  /** Absolute or origin-relative URL to the basemap PMTiles archive. */
  pmtilesUrl: string;
  /** Registered layers, in z-order (first = bottom). Owned by the caller (§10 Phase 2 registry). */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  layers: LayerRegistration<any>[];
  visibility: Record<string, boolean>;
  onDataLoaded?: (counts: Record<string, number>) => void;
  onFeatureClick?: (feature: SelectedFeature | null) => void;
  /** TiTiler base URL + the COG's own URL (e.g. s3://bucket/key.tif) -- omit to skip the layer entirely. */
  heatSurface?: { titilerBaseUrl: string; cogUrl: string };
  className?: string;
}

export function CoolBlockMap({
  pmtilesUrl,
  layers,
  visibility,
  onDataLoaded,
  onFeatureClick,
  heatSurface,
  className,
}: CoolBlockMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const dataRef = useRef<Map<string, unknown>>(new Map());
  const visibilityRef = useRef(visibility);
  const onFeatureClickRef = useRef(onFeatureClick);
  const refreshLayersRef = useRef<() => void>(() => {});
  const setHeatVisibilityRef = useRef<(visible: boolean) => void>(() => {});

  // Refs mirroring props: updated in an effect, never during render (the
  // event handler and the layer-rebuild callback below need the *current*
  // values but must not themselves become effect dependencies that tear
  // down and recreate the map).
  useEffect(() => {
    visibilityRef.current = visibility;
  }, [visibility]);
  useEffect(() => {
    onFeatureClickRef.current = onFeatureClick;
  }, [onFeatureClick]);

  // Map + overlay lifecycle -- created once per mount.
  useEffect(() => {
    if (!containerRef.current) return;
    registerPmtilesProtocol(maplibregl);

    const initialView = readViewStateFromUrl();
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: buildBasemapStyle(pmtilesUrl),
      center: [initialView.longitude, initialView.latitude],
      zoom: initialView.zoom,
      pitch: initialView.pitch,
      bearing: initialView.bearing,
      antialias: true,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

    // Heat surface: a native MapLibre raster layer, not a deck.gl one -- it
    // renders as part of the base map stack, underneath every deck.gl
    // layer (buildings, roads, parcels), which is the point: the surface
    // glows beneath the 3D block, not on top of it (§9 the-45-second-wow ★1).
    if (heatSurface) {
      map.on("load", () => {
        map.addSource(HEAT_SOURCE_ID, {
          type: "raster",
          tiles: [buildHeatSurfaceTileUrl(heatSurface.titilerBaseUrl, heatSurface.cogUrl)],
          tileSize: 256,
        });
        map.addLayer({
          id: HEAT_LAYER_ID,
          type: "raster",
          source: HEAT_SOURCE_ID,
          paint: { "raster-opacity": 0.85 },
          layout: { visibility: visibilityRef.current["heat-surface"] ?? true ? "visible" : "none" },
        });
      });
      setHeatVisibilityRef.current = (visible: boolean) => {
        if (map.getLayer(HEAT_LAYER_ID)) {
          map.setLayoutProperty(HEAT_LAYER_ID, "visibility", visible ? "visible" : "none");
        }
      };
    }

    const overlay = new MapboxOverlay({
      layers: [],
      getTooltip: () => null,
      onClick: (info: PickingInfo) => {
        if (info.object && info.layer) {
          onFeatureClickRef.current?.({
            layerId: info.layer.id,
            properties: (info.object as { properties?: Record<string, unknown> }).properties ?? {},
          });
        } else {
          onFeatureClickRef.current?.(null);
        }
      },
    });
    overlayRef.current = overlay;
    map.addControl(overlay);

    function refreshLayers() {
      const built = layers
        .filter((l) => dataRef.current.has(l.id))
        .map((l) => l.buildLayer(dataRef.current.get(l.id), visibilityRef.current[l.id] ?? l.defaultVisible));
      overlay.setProps({ layers: built });
    }
    refreshLayersRef.current = refreshLayers;

    const persistViewState = () => {
      writeViewStateToUrl({
        longitude: map.getCenter().lng,
        latitude: map.getCenter().lat,
        zoom: map.getZoom(),
        pitch: map.getPitch(),
        bearing: map.getBearing(),
      });
    };
    map.on("moveend", persistViewState);

    let cancelled = false;
    Promise.all(
      layers.map(async (layer) => {
        const data = await layer.loadData();
        if (!cancelled) dataRef.current.set(layer.id, data);
      }),
    ).then(() => {
      if (cancelled) return;
      refreshLayers();
      onDataLoaded?.(
        Object.fromEntries(
          layers.map((l) => {
            const d = dataRef.current.get(l.id) as { features?: unknown[] } | undefined;
            return [l.id, d?.features?.length ?? 0];
          }),
        ),
      );
    });

    return () => {
      cancelled = true;
      map.off("moveend", persistViewState);
      map.remove();
      overlayRef.current = null;
    };
    // Layers, pmtilesUrl, heatSurface and onDataLoaded are fixed for the
    // app's lifetime (one locked neighborhood, §1.3) -- not re-run on change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Visibility changes -- rebuild the deck.gl layers and toggle the heat
  // raster layer's paint property. No re-fetch, no map teardown.
  useEffect(() => {
    refreshLayersRef.current();
    setHeatVisibilityRef.current(visibility["heat-surface"] ?? true);
  }, [visibility]);

  return <div ref={containerRef} className={className} style={{ width: "100%", height: "100%" }} />;
}
