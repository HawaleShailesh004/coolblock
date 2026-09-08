import path from "node:path";
import type { NextConfig } from "next";

// Env lives at the monorepo root (one .env for the whole stack, see
// .env.example) -- Next.js only auto-loads .env files from its own app
// directory, so the root file is loaded explicitly here.
try {
  process.loadEnvFile(path.resolve(__dirname, "..", "..", ".env"));
} catch {
  // .env not present (e.g. CI) -- NEXT_PUBLIC_PMTILES_URL falls back to its
  // hardcoded default in app/map/page.tsx.
}

// Every local service this app's client actually talks to (§13 hardening:
// a real CSP, scoped to what's really used -- not '*'). All four are
// self-hosted (docs/adr/0022-*.md finished the last live-external
// dependency, the basemap's glyphs/sprite), so this list is exhaustive
// for local dev; a production deploy would replace these with its real
// hostnames, not add new ones.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TITILER_URL = process.env.TITILER_URL ?? "http://localhost:8090";
const MINIO_URL = "http://localhost:9000"; // pmtiles/glyphs/sprite -- see NEXT_PUBLIC_PMTILES_URL/NEXT_PUBLIC_MAP_ASSETS_URL
const LOCAL_ORIGINS = [API_URL, TITILER_URL, MINIO_URL].join(" ");

// **Disclosed tradeoff, not a silently weakened CSP**: `script-src`
// includes 'unsafe-inline' because Next.js's App Router injects its own
// hydration/RSC bootstrap scripts inline, and a nonce-based strict CSP
// (Next's documented alternative) needs per-request middleware this pass
// didn't add -- doing that without a browser available to verify the map
// (WebGL/deck.gl, the single most important demo surface) still renders
// correctly was judged a worse risk than shipping a real-but-imperfect
// CSP. Every other directive here is load-bearing: no external script
// origins, no plugins/embeds, no framing (clickjacking), and connect-src
// is scoped to exactly the three local services above -- worker-src/img-src
// allow 'blob:' for maplibre-gl's own web worker and canvas tile decoding.
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  `connect-src 'self' ${LOCAL_ORIGINS}`,
  `img-src 'self' data: blob: ${LOCAL_ORIGINS}`,
  "style-src 'self' 'unsafe-inline'",
  "script-src 'self' 'unsafe-inline'",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@coolblock/ui", "@coolblock/schema", "@coolblock/map"],
  env: {
    NEXT_PUBLIC_PMTILES_URL: process.env.NEXT_PUBLIC_PMTILES_URL,
    NEXT_PUBLIC_MAP_ASSETS_URL: process.env.NEXT_PUBLIC_MAP_ASSETS_URL,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_TITILER_URL: process.env.TITILER_URL,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: CONTENT_SECURITY_POLICY },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
