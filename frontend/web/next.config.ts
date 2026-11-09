import type { NextConfig } from "next";
const api = (process.env.API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const nextConfig: NextConfig = {
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  devIndicators: false,
  // Match FastAPI's request limit; Next otherwise truncates large project uploads at 10 MB.
  experimental: { proxyClientMaxBodySize: 24_000_000, proxyTimeout: 120_000 },
  async redirects() {
    return [
      { source: "/", destination: "/upload", permanent: false },
      {
        source: "/projects/:id",
        destination: "/projects/:id/convert",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health", destination: `${api}/health` },
    ];
  },
};
export default nextConfig;
