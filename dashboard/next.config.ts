import path from "path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname),
  },
  serverExternalPackages: [],
  experimental: {
    // Allow server actions / route handlers to read files outside the
    // project root (e.g. the agent's ../data directory).
    serverActions: {
      bodySizeLimit: "2mb",
    },
  },
  // Permit imports from the parent directory so data-reader.ts can
  // resolve paths relative to COPY_AGENT_DATA_DIR.
  outputFileTracingRoot: undefined,
};

export default nextConfig;
