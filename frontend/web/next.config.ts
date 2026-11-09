import type { NextConfig } from "next";
const api = (process.env.API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
// GITHUB_PAGES=true builds static files for https://aadituh.github.io/LegacyLift/.
// Pages has no server, so that build has no rewrites or redirects and the browser
// calls NEXT_PUBLIC_API_URL directly.
const pages = process.env.GITHUB_PAGES === "true";
const basePath = pages ? "/LegacyLift" : "";
const nextConfig: NextConfig = {
  output: pages
    ? "export"
    : process.env.NEXT_OUTPUT === "standalone"
      ? "standalone"
      : undefined,
  basePath: basePath || undefined,
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
  images: { unoptimized: pages },
  devIndicators: false,
  // Match FastAPI's request limit; Next otherwise truncates large project uploads at 10 MB.
  experimental: { proxyClientMaxBodySize: 24_000_000, proxyTimeout: 120_000 },
  ...(!pages && {
    async redirects() {
      return [
        { source: "/", destination: "/upload", permanent: false },
        {
          source: "/projects/:id/:screen(convert|export)",
          destination: "/:screen?project=:id",
          permanent: false,
        },
        {
          source: "/projects/:id",
          destination: "/convert?project=:id",
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
  }),
};
export default nextConfig;
