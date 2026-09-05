import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

/**
 * Serves the Phase 1 vector layers exported by scripts/export_map_layers.py
 * for the map app. A deliberate, temporary shortcut for Phase 2 ("get
 * pixels on screen") -- Phase 7 replaces this with the real FastAPI +
 * PostGIS + PMTiles serving path. The source of truth stays
 * data/derived/edison-eastlake/*.geojson; nothing is duplicated into
 * apps/web/public.
 */
const ALLOWED_LAYERS = new Set(["buildings", "roads", "parcels"]);

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
