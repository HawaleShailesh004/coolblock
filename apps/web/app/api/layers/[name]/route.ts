import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

/**
 * Serves the static vector layers exported by scripts/export_map_layers.py
 * for the map app -- buildings/roads/parcels/candidates/population/hvi, the
 * layers that don't change per-user or per-request. Phase 7 built the real
 * FastAPI + PostGIS path for what *does* change per user (plans, live
 * solves -- see apps/web/lib/api.ts); PMTiles/vector-tiling this static set
 * too is a disclosed, deliberate deferral (docs/adr/0017-*.md) -- at this
 * neighborhood's scale (a few thousand features per layer), plain GeoJSON
 * via deck.gl's GeoJsonLayer is well within the plan's own "20k features at
 * 60fps" bar (§3.3), so a tiling pipeline would be solving a scale problem
 * this neighborhood doesn't have yet. The source of truth stays
 * data/derived/edison-eastlake/*.geojson; nothing is duplicated into
 * apps/web/public.
 */
const ALLOWED_LAYERS = new Set([
  "buildings",
  "roads",
  "parcels",
  "candidates",
  "optimizer_selection",
  "population",
  "hvi",
]);

const DERIVED_DIR = path.resolve(process.cwd(), "..", "..", "data", "derived", "edison-eastlake");

export async function GET(_request: Request, { params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  if (!ALLOWED_LAYERS.has(name)) {
    return NextResponse.json({ error: `unknown layer '${name}'` }, { status: 404 });
  }

  const filePath = path.join(DERIVED_DIR, `${name}.geojson`);
  try {
    const contents = await readFile(filePath, "utf-8");
    return new NextResponse(contents, {
      headers: { "Content-Type": "application/geo+json", "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { error: `${name}.geojson not found -- run: uv run python scripts/export_map_layers.py` },
      { status: 404 },
    );
  }
}
