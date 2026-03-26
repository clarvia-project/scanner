import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

interface CategoryData {
  slug: string;
  label: string;
  description: string;
  total: number;
  avg_score: number;
  max_score: number;
  by_type: Record<string, number>;
}

async function fetchCategory(slug: string): Promise<CategoryData | null> {
  try {
    const res = await fetch(`${API_BASE}/v1/categories/${slug}?limit=0`, {
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
    },
    twitter: {
      card: "summary",
      title,
      description,
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
      {children}
    </>
  );
}
