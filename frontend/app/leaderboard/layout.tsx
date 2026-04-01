import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

interface LeaderboardTool {
  rank: number;
  name: string;
  url?: string;
  score: number;
  clarvia_score?: number;
  rating?: string;
  category?: string;
  service_type?: string;
  scan_id?: string;
  description?: string;
}

async function fetchLeaderboard(limit = 10): Promise<LeaderboardTool[]> {
  try {
    const res = await fetch(`${API_BASE}/v1/leaderboard?limit=${limit}`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      return data.leaderboard ?? [];
    }
  } catch {
    /* ignore */
  }
  return [];
}

export const metadata: Metadata = {
  title: "AI Agent Tool Leaderboard — Top AEO Scores | Clarvia",
  description:
    "The definitive ranking of AI agent tools by AEO score. See which MCP servers, APIs, CLIs, and skills rank highest for agent readiness across 27,906+ indexed tools.",
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
      "Top-ranked MCP servers and AI agent tools by AEO score. 27,906+ tools analyzed.",
  },
  alternates: {
    canonical: "https://clarvia.art/leaderboard",
  },
};

export default async function LeaderboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const tools = await fetchLeaderboard(10);

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
      logo: {
        "@type": "ImageObject",
        url: "https://clarvia.art/clarvia-owl.png",
      },
    },
    mainEntity: {
      "@type": "ItemList",
      name: "Top AEO-Scoring AI Agent Tools",
      description:
        "The highest-scoring MCP servers, APIs, and AI agent tools ranked by Clarvia AEO score.",
      numberOfItems: tools.length,
      itemListOrder: "https://schema.org/ItemListOrderDescending",
      itemListElement: tools.map((tool, idx) => ({
        "@type": "ListItem",
        position: tool.rank ?? idx + 1,
        item: {
          "@type": "SoftwareApplication",
          name: tool.name,
          description:
            tool.description ??
            `${tool.name} — AEO score ${tool.score ?? tool.clarvia_score ?? "N/A"}/100. Rated ${tool.rating ?? "N/A"}.`,
          url: tool.scan_id
            ? `https://clarvia.art/tool/${tool.scan_id}`
            : tool.url ?? "#",
          applicationCategory: "DeveloperApplication",
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: ((tool.score ?? tool.clarvia_score ?? 0) / 10).toFixed(
              1
            ),
            bestRating: "10",
            worstRating: "0",
            ratingCount: "1",
          },
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
          name: "Leaderboard",
          item: "https://clarvia.art/leaderboard",
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
        name: "Which MCP servers have the highest AEO scores?",
        acceptedAnswer: {
          "@type": "Answer",
          text:
            tools.length > 0
              ? `The top-ranked MCP servers by AEO score are: ${tools
                  .slice(0, 5)
                  .map((t) => `${t.name} (${t.score ?? t.clarvia_score}/100)`)
                  .join(", ")}. These tools scored highest across documentation quality, error handling, structured output, and agent discoverability dimensions.`
              : "Clarvia ranks 27,906+ AI agent tools by AEO score. The top tools score 90+ out of 100 across documentation, error handling, structured outputs, and agent discoverability.",
        },
      },
      {
        "@type": "Question",
        name: "What makes a tool rank high on the Clarvia leaderboard?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "High-ranking tools have: clear OpenAPI or MCP specifications, structured JSON error responses, explicit agent compatibility signals (llms.txt, .well-known/mcp.json), detailed parameter documentation, and active maintenance. AEO score ranges from 0–100 and is recalculated regularly.",
        },
      },
      {
        "@type": "Question",
        name: "How often is the leaderboard updated?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "The Clarvia leaderboard is updated daily as tools are re-scanned and new tools are added to the index. Over 27,906 tools are tracked continuously.",
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
          <h2>Top AI Agent Tools by AEO Score — Clarvia Leaderboard</h2>
          <p>
            The following MCP servers and AI tools scored highest on Clarvia&apos;s
            AEO (AI Engine Optimization) benchmark out of 27,906+ indexed tools.
          </p>
          <ol>
            {tools.slice(0, 10).map((tool, idx) => (
              <li key={idx}>
                <strong>#{tool.rank ?? idx + 1}: {tool.name}</strong> — AEO
                Score: {tool.score ?? tool.clarvia_score ?? "N/A"}/100 (
                {tool.rating ?? "N/A"}).{" "}
                {tool.url && (
                  <a href={tool.url}>
                    {tool.url}
                  </a>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
      {children}
    </>
  );
}
