import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

interface ToolData {
  name?: string;
  description?: string;
  clarvia_score?: number;
  category?: string;
  tags?: string[];
  url?: string;
  service_type?: string;
  rating?: string;
}

async function fetchTool(id: string): Promise<ToolData | null> {
  try {
    const toolId = id;
    const res = await fetch(`${API_BASE}/v1/services/${toolId}`, {
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
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const tool = await fetchTool(id);

  if (!tool?.name) {
    return {
      title: "Tool Profile — Clarvia",
      description: "AEO score and agent readiness analysis on Clarvia.",
    };
  }

  const score = tool.clarvia_score != null ? Math.round(tool.clarvia_score) : null;
  const title = score != null
    ? `${tool.name} — Clarvia Score ${score}/100`
    : `${tool.name} — Clarvia AEO Profile`;
  const description = tool.description
    ? `${tool.description.slice(0, 120)} | AEO score: ${score ?? "N/A"}/100 on Clarvia.`
    : `AEO agent readiness score for ${tool.name}. Analyzed on Clarvia — the standard for AI Engine Optimization.`;

  // Build dynamic OG image URL with tool metadata
  const ogParams = new URLSearchParams({ type: "tool", name: tool.name });
  if (score != null) ogParams.set("score", String(score));
  if (tool.service_type) ogParams.set("stype", tool.service_type);
  if (tool.category) ogParams.set("category", tool.category);
  const ogImageUrl = `/api/og?${ogParams.toString()}`;

  return {
    title,
    description,
    keywords: [
      tool.name,
      "AEO score",
      "AI Engine Optimization",
      "MCP server",
      "agent readiness",
      tool.category ?? "",
      ...(tool.tags ?? []),
    ].filter(Boolean),
    openGraph: {
      title,
      description,
      url: `https://clarvia.art/tool/${id}`,
      siteName: "Clarvia",
      type: "website",
      images: [
        {
          url: ogImageUrl,
          width: 1200,
          height: 630,
          alt: `${tool.name} — Clarvia AEO Score`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [ogImageUrl],
    },
  };
}

export default async function ToolLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const tool = await fetchTool(id);

  const jsonLd = tool?.name
    ? {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        name: tool.name,
        description: tool.description ?? `AI agent tool scored on Clarvia`,
        url: tool.url ?? `https://clarvia.art/tool/${id}`,
        applicationCategory: "DeveloperApplication",
        ...(tool.clarvia_score != null && {
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: (tool.clarvia_score / 10).toFixed(1),
            bestRating: "10",
            worstRating: "0",
            ratingCount: "1",
            reviewCount: "1",
          },
        }),
        ...(tool.tags?.length && { keywords: tool.tags.join(", ") }),
        review: {
          "@type": "Review",
          reviewBody: `Clarvia AEO Score: ${tool.clarvia_score ?? "N/A"}/100. Category: ${tool.category ?? "unknown"}. Rating: ${tool.rating ?? "N/A"}.`,
          author: {
            "@type": "Organization",
            name: "Clarvia",
            url: "https://clarvia.art",
          },
        },
      }
    : null;

  // Build a self-contained answer block visible to AI crawlers (SSR)
  const answerBlock = tool?.name
    ? (() => {
        const score = tool.clarvia_score != null ? Math.round(tool.clarvia_score) : null;
        const rating = tool.rating ?? (score != null ? (score >= 70 ? "Strong" : score >= 40 ? "Moderate" : "Basic") : "Unknown");
        const category = tool.category ?? "developer tool";
        const stype = tool.service_type ?? "tool";
        const desc = tool.description
          ? tool.description.replace(/<[^>]+>/g, "").slice(0, 150)
          : null;

        const lines = [
          `${tool.name} is a ${stype.replace("_", " ")} in the ${category} category.`,
          desc ? desc : null,
          score != null
            ? `Clarvia AEO Score: ${score}/100 (${rating}). The AEO score measures how easily AI agents can discover and use this tool, covering API accessibility, data structuring, agent compatibility, and trust signals.`
            : null,
          tool.url ? `Official resource: ${tool.url}` : null,
          `View full analysis and badge at https://clarvia.art/tool/${id}`,
        ].filter(Boolean);

        return lines.join(" ");
      })()
    : null;

  return (
    <>
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
      {answerBlock && (
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
          <h1>{tool!.name} — Clarvia AEO Score {tool!.clarvia_score ?? "N/A"}/100</h1>
          <p>{answerBlock}</p>
        </div>
      )}
      {children}
    </>
  );
}
