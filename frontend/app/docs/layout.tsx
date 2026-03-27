import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "API Documentation — Clarvia",
  description:
    "Clarvia API documentation. Scan URLs, query the leaderboard, compare tools, and integrate AEO scoring into your CI/CD pipeline.",
  openGraph: {
    title: "Clarvia API Documentation",
    description:
      "REST API for AEO scanning, tool discovery, and agent readiness scoring.",
    url: "https://clarvia.art/docs",
  },
  alternates: {
    canonical: "https://clarvia.art/docs",
  },
};

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
