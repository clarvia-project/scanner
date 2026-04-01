import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

interface TrendingTool {
  name: string;
  scan_id?: string;
  url?: string;
  description?: string;
  clarvia_score?: number;
  score?: number;
}

async function fetchTrending(): Promise<TrendingTool[]> {
  try {
    const res = await fetch(`${API_BASE}/v1/trending`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      return (data.top_tools ?? data.leaderboard ?? []).slice(0, 10);
    }
  } catch {
    /* ignore */
  }
  return [];
}

export const metadata: Metadata = {
  title: "Trending AI Agent Tools — Clarvia",
  description:
    "Discover the hottest MCP servers, APIs, CLIs, and agent skills trending right now. Ranked by AEO score and momentum across 27,843+ indexed tools.",
  keywords: [
    "trending MCP servers",
    "best AI agent tools 2026",
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
      "Discover the hottest MCP servers and agent tools trending now. AEO scores for 27,843+ tools.",
  },
  alternates: {
    canonical: "https://clarvia.art/trending",
  },
};

export default async function TrendingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const tools = await fetchTrending();

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
      logo: {
        "@type": "ImageObject",
        url: "https://clarvia.art/clarvia-owl.png",
      },
    },
    mainEntity: {
      "@type": "ItemList",
      name: "Trending MCP Servers and AI Agent Tools",
      description: "Top-performing AI agent tools ranked by Clarvia AEO score this week.",
      numberOfItems: tools.length,
      itemListOrder: "https://schema.org/ItemListOrderDescending",
      itemListElement: tools.map((tool, idx) => ({
        "@type": "ListItem",
        position: idx + 1,
        item: {
          "@type": "SoftwareApplication",
          name: tool.name,
          description:
            tool.description ??
            `${tool.name} — AEO score ${tool.clarvia_score ?? tool.score ?? "N/A"}/100`,
          url: tool.scan_id
            ? `https://clarvia.art/tool/${tool.scan_id}`
            : tool.url ?? "#",
          applicationCategory: "DeveloperApplication",
          ...((tool.clarvia_score ?? tool.score) != null && {
            aggregateRating: {
              "@type": "AggregateRating",
              ratingValue: ((tool.clarvia_score ?? tool.score ?? 0) / 10).toFixed(1),
              bestRating: "10",
              worstRating: "0",
              ratingCount: "1",
            },
          }),
        },
      })),
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

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "Which MCP servers are trending right now?",
        acceptedAnswer: {
          "@type": "Answer",
          text:
            tools.length > 0
              ? `The most popular MCP servers this week by AEO score are: ${tools
                  .slice(0, 5)
                  .map((t) => `${t.name} (${t.clarvia_score ?? t.score ?? "N/A"}/100)`)
                  .join(", ")}. Ranked across 27,843+ indexed tools on Clarvia.`
              : "Clarvia tracks 27,843+ MCP servers and AI agent tools. Trending rankings are updated weekly based on AEO scores and ecosystem adoption.",
        },
      },
      {
        "@type": "Question",
        name: "How does Clarvia determine trending tools?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Clarvia's trending algorithm combines AEO score, week-over-week score improvement, search query volume, and new registry listings. Tools that are both high-quality (high AEO score) and gaining momentum rank highest.",
        },
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      {tools.length > 0 && (
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            width: "1px",
            height: "1px",
            overflow: "hidden",
            clip: "rect(0,0,0,0)",
            whiteSpace: "nowrap",
          }}
        >
          <h2>Trending AI Agent Tools This Week — Clarvia</h2>
          <p>Top-performing MCP servers and AI tools ranked by AEO score from 27,843+ indexed tools.</p>
          <ol>
            {tools.slice(0, 10).map((tool, idx) => (
              <li key={idx}>
                <strong>#{idx + 1}: {tool.name}</strong> — AEO Score:{" "}
                {tool.clarvia_score ?? tool.score ?? "N/A"}/100.{" "}
                {tool.description ? tool.description.slice(0, 120) : ""}
              </li>
            ))}
          </ol>
        </div>
      )}
      {children}
    </>
  );
}
