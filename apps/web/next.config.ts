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
//
// **These must read the same env vars the client code reads.** They did not,
// and it shipped: the CSP read `TITILER_URL` while `app/map/page.tsx` reads
// `NEXT_PUBLIC_TITILER_URL`. Setting the documented `NEXT_PUBLIC_` var on a
// real deploy therefore pointed the map at the deployed TiTiler while leaving
// the CSP pinned to `http://localhost:8090`, so every heat tile was refused by
// the browser ("Connecting to ... violates the ... Content Security Policy")
// and the heat surface -- the product's central visual -- silently never
// rendered in production. Nothing errored server-side; the layer was just
// absent. Deriving both from one list is what stops that recurring.
const originOf = (url: string | undefined): string | null => {
  if (!url) return null;
  try {
    return new URL(url).origin;
  } catch {
    return null; // a relative/same-origin value is already covered by 'self'
  }
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TITILER_URL = process.env.NEXT_PUBLIC_TITILER_URL ?? process.env.TITILER_URL ?? "http://localhost:8090";
const MINIO_URL = "http://localhost:9000"; // pmtiles/glyphs/sprite -- see NEXT_PUBLIC_PMTILES_URL/NEXT_PUBLIC_MAP_ASSETS_URL
const LOCAL_ORIGINS = [
  ...new Set(
    [
      API_URL,
      TITILER_URL,
      MINIO_URL,
      // Same-origin on a Vercel deploy (served from /tiles/...), cross-origin
      // when pointed at object storage -- include whichever it actually is.
      process.env.NEXT_PUBLIC_PMTILES_URL,
      process.env.NEXT_PUBLIC_MAP_ASSETS_URL,
    ]
      .map(originOf)
      .filter((o): o is string => o !== null),
  ),
].join(" ");

// **Disclosed tradeoff, not a silently weakened CSP**: `script-src`
// includes 'unsafe-inline' because Next.js's App Router injects its own
// hydration/RSC bootstrap scripts inline, and a nonce-based strict CSP
// (Next's documented alternative) needs per-request middleware this pass
// didn't add. Every other directive here is load-bearing: no external
// script origins, no plugins/embeds, and connect-src is scoped to
// exactly the three local services above -- worker-src/img-src allow
// 'blob:' for maplibre-gl's own web worker and canvas tile decoding.
//
// `frame-ancestors 'none'`: nothing in this app frames another route of
// itself (docs/adr/0027-*.md briefly tried embedding /map in an iframe on
// the marketing homepage, found a real hydration-mismatch quirk specific
// to that embedded context plus the real backend cost of a second full
// app instance loading per marketing pageview, and dropped it in favor
// of a screenshot + a direct link -- so the strict, no-framing-at-all
// policy is correct again, not merely the original default).
//
// **`'unsafe-eval'` is added in development only, and this is not a
// guess** -- confirmed by actually reproducing the break: with a strict
// script-src, clicking "Run optimizer" in `next dev` threw
// `Evaluating a string as JavaScript violates ... 'unsafe-eval' is not
// an allowed source` and the optimizer never ran at all, the single most
// important feature in the entire product. A production build
// (`next build && next start`) completed a real solve with the exact
// same strict script-src and no eval error -- Next's webpack dev-mode
// tooling (HMR/eval-source-map) is what needs `eval`, not this app's own
// code or its dependencies (React, maplibre-gl, deck.gl). Since the demo
// itself runs via `next dev` (`scripts/dev.sh`), shipping the strict
// policy unconditionally would have silently broken the actual
// checkpoint this ADR exists to protect -- so development gets the
// looser policy, production gets the strict one, and this asymmetry is
// the point, not an oversight.
const IS_DEV = process.env.NODE_ENV !== "production";
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  `connect-src 'self' ${LOCAL_ORIGINS}`,
  `img-src 'self' data: blob: ${LOCAL_ORIGINS}`,
  "style-src 'self' 'unsafe-inline'",
  `script-src 'self' 'unsafe-inline'${IS_DEV ? " 'unsafe-eval'" : ""}`,
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
    // Not in the allowlist until now -- the same silent-override bug
    // docs/adr/0023-*.md already found once for NEXT_PUBLIC_MAP_ASSETS_URL
    // would otherwise repeat here for anyone deploying with a real heat
    // surface COG URL (docs/DEPLOYMENT.md).
    NEXT_PUBLIC_HEAT_SURFACE_COG_URL: process.env.NEXT_PUBLIC_HEAT_SURFACE_COG_URL,
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
