import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

interface Tool {
  name: string;
  url?: string;
  description?: string;
  clarvia_score?: number;
  service_type?: string;
  scan_id?: string;
}

interface CategoryData {
  slug: string;
  label: string;
  description: string;
  total: number;
  avg_score: number;
  max_score: number;
  by_type: Record<string, number>;
  tools?: Tool[];
}

async function fetchCategory(slug: string): Promise<CategoryData | null> {
  try {
    const res = await fetch(`${API_BASE}/v1/categories/${slug}?limit=10`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) return res.json();
  } catch {
    /* ignore */
  }
  return null;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const category = await fetchCategory(slug);

  const label = category?.label ?? slug.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const total = category?.total ?? 0;
  const avgScore = category?.avg_score ?? 0;

  const title = `Best ${label} Tools for AI Agents — Clarvia`;
  const description = category?.description
    ? `${category.description.slice(0, 130)} | ${total} tools ranked by AEO score on Clarvia.`
    : `Discover the top ${label.toLowerCase()} tools for AI agents, ranked by AEO score. ${total} tools analyzed. Average score: ${avgScore}/100.`;

  return {
    title,
    description,
    keywords: [
      `${label} MCP servers`,
      `best ${label.toLowerCase()} tools for AI`,
      `${label} AEO score`,
      `AI agent ${label.toLowerCase()}`,
      "MCP server ranking",
      "AEO score",
      "AI Engine Optimization",
      "agent-ready tools",
      "Clarvia",
    ],
    openGraph: {
      title,
      description,
      url: `https://clarvia.art/categories/${slug}`,
      siteName: "Clarvia",
      type: "website",
      images: [
        {
          url: "/api/og",
          width: 1200,
          height: 630,
          alt: `${label} — Clarvia AEO Tools`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: ["/api/og"],
    },
    alternates: {
      canonical: `https://clarvia.art/categories/${slug}`,
    },
  };
}

export default async function CategoryLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const category = await fetchCategory(slug);

  const label = category?.label ?? slug.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const total = category?.total ?? 0;

  const jsonLd = category
    ? {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        name: `Best ${label} Tools for AI Agents`,
        description: category.description || `Top ${label} tools ranked by Clarvia AEO score.`,
        url: `https://clarvia.art/categories/${slug}`,
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
          name: `${label} Tools Ranked by AEO Score`,
          description: `${total} ${label} tools analyzed and ranked by AI Engine Optimization score.`,
          numberOfItems: total,
          itemListOrder: "https://schema.org/ItemListOrderDescending",
          itemListElement: (category?.tools ?? []).slice(0, 10).map((tool, idx) => ({
            "@type": "ListItem",
            position: idx + 1,
            item: {
              "@type": "SoftwareApplication",
              name: tool.name,
              description: tool.description ?? `${tool.name} — AEO score ${tool.clarvia_score ?? "N/A"}/100`,
              url: tool.scan_id ? `https://clarvia.art/tool/${tool.scan_id}` : (tool.url ?? "#"),
              applicationCategory: "DeveloperApplication",
              ...(tool.clarvia_score != null && {
                aggregateRating: {
                  "@type": "AggregateRating",
                  ratingValue: (tool.clarvia_score / 10).toFixed(1),
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
              name: "Categories",
              item: "https://clarvia.art/categories",
            },
            {
              "@type": "ListItem",
              position: 3,
              name: label,
              item: `https://clarvia.art/categories/${slug}`,
            },
          ],
        },
      }
    : null;

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: `What are the best ${label} tools for AI agents?`,
        acceptedAnswer: {
          "@type": "Answer",
          text: `Clarvia ranks ${total} ${label} tools by AEO (AI Engine Optimization) score. The highest-ranked tools have clear documentation, structured outputs, and reliable error handling — making them ideal for autonomous agent integration.`,
        },
      },
      {
        "@type": "Question",
        name: `How does Clarvia score ${label} tools?`,
        acceptedAnswer: {
          "@type": "Answer",
          text: `Clarvia's AEO score evaluates tools across six dimensions: documentation quality, error handling, structured output, agent discoverability, security posture, and ecosystem health. Scores range from 0–100.`,
        },
      },
      {
        "@type": "Question",
        name: `What is AEO score for ${label} tools?`,
        acceptedAnswer: {
          "@type": "Answer",
          text: `AEO (AI Engine Optimization) score measures how well a tool supports AI agent integration. For ${label} tools, the average score is ${category?.avg_score ?? "N/A"}/100. Tools scoring 70+ are considered agent-ready.`,
        },
      },
    ],
  };

  return (
    <>
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      {/* Server-rendered content for AI crawlers — hidden visually, indexed by bots */}
      {category && (category.tools ?? []).length > 0 && (
        <div aria-hidden="true" style={{ position: "absolute", width: "1px", height: "1px", overflow: "hidden", clip: "rect(0,0,0,0)", whiteSpace: "nowrap" }}>
          <h2>Top {label} Tools for AI Agents — AEO Ranked</h2>
          <p>{category.description || `Clarvia ranks ${total} ${label} tools by AEO score. Average score: ${category.avg_score?.toFixed(0) ?? "N/A"}/100.`}</p>
          <ol>
            {(category.tools ?? []).slice(0, 10).map((tool, idx) => (
              <li key={idx}>
                <strong>{tool.name}</strong> — AEO Score: {tool.clarvia_score?.toFixed(0) ?? "N/A"}/100.{" "}
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
