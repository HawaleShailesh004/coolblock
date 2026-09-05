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

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@coolblock/ui", "@coolblock/schema", "@coolblock/map"],
  env: {
    NEXT_PUBLIC_PMTILES_URL: process.env.NEXT_PUBLIC_PMTILES_URL,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_TITILER_URL: process.env.TITILER_URL,
  },
};

export default nextConfig;
