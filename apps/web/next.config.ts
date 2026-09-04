import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@coolblock/ui", "@coolblock/schema", "@coolblock/map"],
};

export default nextConfig;
