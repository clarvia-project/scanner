import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Trending AI Agent Tools — Clarvia",
  description:
    "Discover the hottest MCP servers, APIs, CLIs, and agent skills trending right now. Ranked by AEO score and momentum across 15,400+ indexed tools.",
  keywords: [
    "trending MCP servers",
    "best AI agent tools 2025",
    "top MCP servers",
    "AEO score trending",
    "agent-ready tools",
    "MCP server ranking",
    "AI Engine Optimization",
    "Clarvia trending",
  ],
  openGraph: {
    title: "Trending AI Agent Tools — Clarvia",
    description:
      "Discover the hottest MCP servers, APIs, CLIs, and agent skills trending right now.",
    url: "https://clarvia.art/trending",
    siteName: "Clarvia",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Trending AI Agent Tools — Clarvia",
    description:
      "Discover the hottest MCP servers and agent tools trending now. AEO scores for 15,400+ tools.",
  },
  alternates: {
    canonical: "https://clarvia.art/trending",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  name: "Trending AI Agent Tools",
  description:
    "The most popular and fastest-rising MCP servers, APIs, CLIs, and AI agent skills, ranked by Clarvia AEO score.",
  url: "https://clarvia.art/trending",
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
        name: "Trending",
        item: "https://clarvia.art/trending",
      },
    ],
  },
};

export default function TrendingLayout({
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
