import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Register Your Tool — Clarvia",
  description:
    "Submit your API, MCP server, or CLI tool to the Clarvia directory. Get scored, earn a badge, and increase your discoverability to AI agents.",
  openGraph: {
    title: "Register Your Tool on Clarvia",
    description:
      "Submit your tool for AEO scoring and agent discoverability.",
    url: "https://clarvia.art/register",
  },
  alternates: {
    canonical: "https://clarvia.art/register",
  },
};

export default function RegisterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
