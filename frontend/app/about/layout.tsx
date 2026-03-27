import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About Clarvia — The AEO Standard for AI Agents",
  description:
    "Clarvia is the AI Engine Optimization (AEO) standard. We score how easily AI agents can discover and use any API, MCP server, or tool.",
  openGraph: {
    title: "About Clarvia",
    description:
      "The AEO standard for AI agent discoverability and trust.",
    url: "https://clarvia.art/about",
  },
  alternates: {
    canonical: "https://clarvia.art/about",
  },
};

export default function AboutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
