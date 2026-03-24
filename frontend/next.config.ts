import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
};

export default nextConfig;
