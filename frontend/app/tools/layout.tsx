import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Agent Tool Directory — 15,000+ Tools Scored | Clarvia",
  description:
    "Browse and search 15,000+ AI agent tools including MCP servers, APIs, CLI tools, and skills. Every tool scored for agent readiness with the Clarvia AEO standard.",
  openGraph: {
    title: "AI Agent Tool Directory | Clarvia",
    description:
      "Search 15,000+ MCP servers, APIs, CLI tools, and skills scored for agent readiness.",
    url: "https://clarvia.art/tools",
  },
  alternates: {
    canonical: "https://clarvia.art/tools",
  },
};

export default function ToolsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
