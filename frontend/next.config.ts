import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const backend = new URL(
      process.env.INTERNAL_API_URL ?? process.env.SERVER_API_URL ?? "http://localhost:8000",
    );
    backend.pathname = backend.pathname.replace(/\/api\/v1\/?$/, "").replace(/\/$/, "");
    const backendOrigin = backend.toString().replace(/\/$/, "");
    return [
      { source: "/api/:path*", destination: `${backendOrigin}/api/:path*` },
      { source: "/health", destination: `${backendOrigin}/health` },
      { source: "/health/:path*", destination: `${backendOrigin}/health/:path*` },
    ];
  },
};

export default nextConfig;
