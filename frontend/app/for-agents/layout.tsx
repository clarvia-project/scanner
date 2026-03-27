import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "For AI Agents — Clarvia API & MCP Server",
  description:
    "Clarvia endpoints designed for AI agents. Discover tools, get AEO scores, and find the best MCP servers programmatically.",
  openGraph: {
    title: "Clarvia for AI Agents",
    description:
      "Machine-readable API for agent tool discovery and AEO scoring.",
    url: "https://clarvia.art/for-agents",
  },
  alternates: {
    canonical: "https://clarvia.art/for-agents",
  },
};

export default function ForAgentsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
