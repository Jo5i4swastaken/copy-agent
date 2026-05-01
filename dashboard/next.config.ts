import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: [],
  experimental: {
    // Allow server actions / route handlers to read files outside the
    // project root (e.g. the agent's ../data directory).
    serverActions: {
      bodySizeLimit: "2mb",
    },
  },
};

export default nextConfig;
