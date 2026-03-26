import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Agent Tool Leaderboard — Top AEO Scores | Clarvia",
  description:
    "The definitive ranking of AI agent tools by AEO score. See which MCP servers, APIs, CLIs, and skills rank highest for agent readiness across 15,400+ indexed tools.",
  keywords: [
    "MCP server leaderboard",
    "best MCP servers",
    "top AI agent tools",
    "AEO score ranking",
    "agent-ready MCP servers",
    "highest AEO score",
    "AI Engine Optimization leaderboard",
    "Clarvia leaderboard",
  ],
  openGraph: {
    title: "AI Agent Tool Leaderboard — Top AEO Scores | Clarvia",
    description:
      "The definitive ranking of AI agent tools by AEO score. Which MCP servers score highest?",
    url: "https://clarvia.art/leaderboard",
    siteName: "Clarvia",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "AI Agent Tool Leaderboard — Top AEO Scores | Clarvia",
    description:
      "Top-ranked MCP servers and AI agent tools by AEO score. 15,400+ tools analyzed.",
  },
  alternates: {
    canonical: "https://clarvia.art/leaderboard",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  name: "AI Agent Tool Leaderboard — AEO Scores",
  description:
    "Rankings of the best MCP servers, APIs, CLIs, and AI agent skills by Clarvia AEO score. Updated daily.",
  url: "https://clarvia.art/leaderboard",
  publisher: {
    "@type": "Organization",
    name: "Clarvia",
    url: "https://clarvia.art",
  },
  breadcrumb: {
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: "https://clarvia.art",
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Leaderboard",
        item: "https://clarvia.art/leaderboard",
      },
    ],
  },
};

export default function LeaderboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {children}
    </>
  );
}
