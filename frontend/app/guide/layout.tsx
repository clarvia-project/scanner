import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AEO Improvement Guide — Clarvia",
  description:
    "Step-by-step guide to improve your AEO score. Learn how to make your API, MCP server, or tool more discoverable and usable by AI agents.",
  openGraph: {
    title: "AEO Improvement Guide | Clarvia",
    description:
      "Actionable playbook to boost your Clarvia Score and agent readiness.",
    url: "https://clarvia.art/guide",
  },
  alternates: {
    canonical: "https://clarvia.art/guide",
  },
};

export default function GuideLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
