import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Agent Tool Categories — 28,000+ Tools by Category | Clarvia",
  description:
    "Browse AI agent tools by category. Find MCP servers, APIs, CLI tools, and skills ranked by AEO score across developer tools, cloud, database, AI, and more.",
  openGraph: {
    title: "AI Agent Tool Categories | Clarvia",
    description:
      "Browse 28,000+ AI agent tools by category, ranked by AEO (AI Engine Optimization) score.",
    url: "https://clarvia.art/categories",
  },
  alternates: {
    canonical: "https://clarvia.art/categories",
  },
};

export default function CategoriesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
