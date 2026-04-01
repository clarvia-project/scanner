import Link from "next/link";
import Image from "next/image";
import { Metadata } from "next";
import TrendingClient, { TrendingData } from "./TrendingClient";
import Nav from "@/app/components/Nav";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

// ---------------------------------------------------------------------------
// Data fetching (server-side)
// ---------------------------------------------------------------------------

async function fetchTrendingData(): Promise<TrendingData | null> {
  try {
    const res = await fetch(`${API_BASE}/v1/trending?limit=20`, {
      next: { revalidate: 3600 }, // revalidate every hour
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Metadata (SSR)
// ---------------------------------------------------------------------------

export const metadata: Metadata = {
  title: "Trending AI Tools & MCP Servers — Top Ranked by AEO Score | Clarvia",
  description:
    "Discover the top-performing AI tools, MCP servers, and APIs ranked by AEO score. Updated weekly across 27,000+ indexed agent tools on Clarvia.",
  openGraph: {
    title: "Trending AI Tools & MCP Servers — Ranked by AEO Score | Clarvia",
    description:
      "Top-performing agent tools across 27,000+ indexed services. Ranked by AEO (AI Engine Optimization) score.",
    url: "https://clarvia.art/trending",
    siteName: "Clarvia",
    type: "website",
  },
  alternates: {
    canonical: "https://clarvia.art/trending",
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  mcp_server: { label: "MCP", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  api: { label: "API", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  cli_tool: { label: "CLI", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  skill: { label: "Skill", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  general: { label: "General", color: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
};

// ---------------------------------------------------------------------------
// JSON-LD (server-rendered for AI crawlers)
// ---------------------------------------------------------------------------

function TrendingJsonLd({ data }: { data: TrendingData }) {
  const itemList = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Trending AI Tools & MCP Servers — Ranked by AEO Score",
    description: `Top-performing agent tools across ${data.total_indexed.toLocaleString()} indexed services, ranked by AEO (AI Engine Optimization) score on Clarvia.`,
    url: "https://clarvia.art/trending",
    numberOfItems: data.top_tools.length,
    itemListElement: data.top_tools.map((tool, i) => ({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "SoftwareApplication",
        name: tool.name,
        url: tool.url,
        applicationCategory: tool.category,
        description:
          tool.description ||
          `${tool.name} — AEO Score: ${tool.clarvia_score}/100. ${tool.rating} agent readiness.`,
        aggregateRating: {
          "@type": "AggregateRating",
          ratingValue: tool.clarvia_score,
          bestRating: 100,
          worstRating: 0,
          ratingCount: 1,
        },
      },
    })),
  };

  const orgLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "Clarvia",
    url: "https://clarvia.art",
    description:
      "Clarvia indexes and ranks AI tools, MCP servers, and APIs by AEO (AI Engine Optimization) score — a measure of how agent-ready each tool is.",
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(itemList) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(orgLd) }}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Page (Server Component)
// ---------------------------------------------------------------------------

export default async function TrendingPage() {
  const data = await fetchTrendingData();

  return (
    <div className="min-h-screen flex flex-col">
      {/* JSON-LD — server-rendered for AI crawlers */}
      {data && <TrendingJsonLd data={data} />}

      <Nav />

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Hero */}
        <div className="mb-8 space-y-3">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Trending Tools</h1>
            <span className="text-[10px] font-mono px-2 py-1 rounded-full bg-accent/10 text-accent border border-accent/20">
              WEEKLY
            </span>
          </div>
          <p className="text-muted max-w-2xl">
            Top-performing agent tools across{" "}
            <span className="text-foreground font-semibold font-mono">
              {data?.total_indexed?.toLocaleString() || "27,000+"}
            </span>{" "}
            indexed services. Updated weekly.
          </p>
        </div>

        {!data ? (
          <div className="glass-card rounded-xl p-12 text-center">
            <p className="text-muted">Failed to load trending data.</p>
          </div>
        ) : (
          <>
            {/* Service Type Leaders — server-rendered */}
            {data.service_type_leaders && Object.keys(data.service_type_leaders).length > 0 && (
              <section className="mb-10">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                  Category Leaders
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(data.service_type_leaders).map(([type, tool]) => {
                    const typeInfo = TYPE_LABELS[type] || TYPE_LABELS.general;
                    return (
                      <Link
                        key={type}
                        href={tool.scan_id.startsWith("tool_") ? `/tool/${tool.scan_id}` : `/scan/${tool.scan_id}`}
                        className="glass-card rounded-xl p-4 hover:border-accent/30 transition-all text-center group"
                      >
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${typeInfo.color}`}>
                          {typeInfo.label}
                        </span>
                        <div className={`text-2xl font-bold font-mono mt-2 ${scoreColor(tool.clarvia_score)}`}>
                          {tool.clarvia_score}
                        </div>
                        <div className="text-xs font-semibold mt-1 truncate group-hover:text-accent transition-colors">
                          {tool.name}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Top Tools Overall — server-rendered for AI crawlers */}
            <section className="mb-10">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                Top Tools Overall
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {(data.top_tools || []).map((tool, idx) => (
                  <Link
                    key={tool.scan_id}
                    href={tool.scan_id.startsWith("tool_") ? `/tool/${tool.scan_id}` : `/scan/${tool.scan_id}`}
                    className="glass-card rounded-xl p-4 hover:border-accent/30 transition-all group flex flex-col"
                  >
                    <div className="flex items-start gap-3 mb-2">
                      <span className="text-lg font-bold text-muted/30 font-mono w-6 text-right flex-shrink-0">
                        {idx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${(TYPE_LABELS[tool.service_type] || TYPE_LABELS.general).color}`}>
                            {(TYPE_LABELS[tool.service_type] || TYPE_LABELS.general).label}
                          </span>
                          <span className={`text-xs font-mono font-bold ${scoreColor(tool.clarvia_score)}`}>
                            {tool.clarvia_score}
                          </span>
                        </div>
                        <h3 className="text-sm font-semibold truncate group-hover:text-accent transition-colors">
                          {tool.name}
                        </h3>
                      </div>
                    </div>
                    {tool.description && (
                      <p className="text-xs text-muted/70 line-clamp-2 leading-relaxed">
                        {tool.description}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            </section>

            {/* Rising Stars — server-rendered */}
            {(data.rising_stars || []).length > 0 && (
              <section className="mb-10">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  Rising Stars
                  <span className="text-[10px] text-muted font-normal font-mono">
                    Emerging from the ecosystem
                  </span>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {(data.rising_stars || []).map((tool) => (
                    <Link
                      key={tool.scan_id}
                      href={tool.scan_id.startsWith("tool_") ? `/tool/${tool.scan_id}` : `/scan/${tool.scan_id}`}
                      className="glass-card rounded-xl p-4 hover:border-accent/30 transition-all group flex flex-col"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${(TYPE_LABELS[tool.service_type] || TYPE_LABELS.general).color}`}>
                            {(TYPE_LABELS[tool.service_type] || TYPE_LABELS.general).label}
                          </span>
                          <span className={`text-xs font-mono font-bold ${scoreColor(tool.clarvia_score)}`}>
                            {tool.clarvia_score}
                          </span>
                        </div>
                        <h3 className="text-sm font-semibold truncate group-hover:text-accent transition-colors">
                          {tool.name}
                        </h3>
                      </div>
                      {tool.description && (
                        <p className="text-xs text-muted/70 line-clamp-2 leading-relaxed mt-2">
                          {tool.description}
                        </p>
                      )}
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Interactive category filter (client component) */}
            <TrendingClient data={data} />
          </>
        )}
      </main>

      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia — The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}
