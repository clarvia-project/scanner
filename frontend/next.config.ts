import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Prevent source maps from being served to browsers in production
  productionBrowserSourceMaps: false,
  // "standalone" is only needed for Docker-based deployments.
  // Vercel handles builds natively, so we omit output here.
  // For Docker/self-hosted, uncomment: output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "clarvia-api.onrender.com",
      },
    ],
  },
  async redirects() {
    return [
      {
        source: "/openapi.json",
        destination: "https://clarvia-api.onrender.com/openapi.json",
        permanent: false,
      },
      {
        source: "/api/docs",
        destination: "https://clarvia-api.onrender.com/docs",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
