"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Tool {
  name: string;
  url: string;
  description: string;
  category: string;
  service_type: string;
  clarvia_score: number;
  rating: string;
  scan_id: string;
  dimensions: Record<string, number>;
}

interface CategoryData {
  slug: string;
  label: string;
  description: string;
  total: number;
  avg_score: number;
  max_score: number;
  by_type: Record<string, number>;
  tools: Tool[];
  offset: number;
  limit: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  mcp_server: {
    label: "MCP",
    color: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  },
  api: {
    label: "API",
    color: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  },
  cli_tool: {
    label: "CLI",
    color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  },
  skill: {
    label: "Skill",
    color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  },
  general: {
    label: "General",
    color: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  },
};

const SERVICE_TYPE_TABS = [
  { id: "all", label: "All" },
  { id: "mcp_server", label: "MCP" },
  { id: "api", label: "API" },
  { id: "skill", label: "Skill" },
  { id: "cli_tool", label: "CLI" },
];

// Category FAQ templates
const CATEGORY_FAQS: Record<
  string,
  { question: string; answer: string }[]
> = {};

function generateFAQs(
  label: string,
  total: number,
  avgScore: number
): { question: string; answer: string }[] {
  return [
    {
      question: `What are the best ${label} tools for AI agents?`,
      answer: `Clarvia indexes and ranks ${total.toLocaleString()} ${label.toLowerCase()} tools by AEO (AI Engine Optimization) score. The AEO score measures how easily AI agents can discover and use each tool, considering API accessibility, data structuring, agent compatibility, and trust signals. Browse the ranked list above to find the best options.`,
    },
    {
      question: `What is the AEO score for ${label} tools?`,
      answer: `The average AEO score across ${label.toLowerCase()} tools is ${avgScore.toFixed(1)} out of 100. AEO scores measure agent-readiness across four dimensions: API Accessibility, Data Structuring, Agent Compatibility, and Trust Signals. Higher scores indicate tools that AI agents can more easily discover and integrate with.`,
    },
    {
      question: `How are ${label} tools ranked on Clarvia?`,
      answer: `Tools are ranked by their Clarvia AEO Score, which is computed by scanning each tool's API surface, documentation, error handling, and protocol support. The score is broken down into four weighted dimensions. Tools with higher scores appear first, making it easy to find the most agent-friendly options.`,
    },
    {
      question: `Can AI agents automatically use these ${label} tools?`,
      answer: `Tools with high AEO scores (70+) are generally well-suited for AI agent integration. Many listed tools support the Model Context Protocol (MCP), have structured API documentation, and provide clear error handling — all factors that make autonomous agent usage reliable.`,
    },
  ];
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function scoreBg(score: number) {
  if (score >= 70) return "glow-green";
  if (score >= 40) return "glow-yellow";
  return "glow-red";
}

function TypeBadge({ type }: { type: string }) {
  const info = TYPE_LABELS[type] || TYPE_LABELS.general;
  return (
    <span
      className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${info.color}`}
    >
      {info.label}
    </span>
  );
}

function getFaviconUrl(url: string): string | null {
  if (!url) return null;
  try {
    const domain = new URL(
      url.startsWith("http") ? url : `https://${url}`
    ).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return null;
  }
}

function ServiceIcon({ url, name }: { url: string; name: string }) {
  const [error, setError] = useState(false);
  const favicon = getFaviconUrl(url);

  if (!favicon || error) {
    return (
      <div className="w-8 h-8 rounded-lg bg-card-border/40 flex items-center justify-center flex-shrink-0">
        <span className="text-xs font-bold text-muted/70">
          {(name || "?").charAt(0).toUpperCase()}
        </span>
      </div>
    );
  }

  return (
    <img
      src={favicon}
      alt=""
      width={20}
      height={20}
      className="w-8 h-8 rounded-lg bg-card-border/30 p-1.5 flex-shrink-0 object-contain"
      onError={() => setError(true)}
    />
  );
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1)
    return (
      <span className="badge-gold text-[10px] font-bold px-2 py-0.5 rounded-full">
        #1
      </span>
    );
  if (rank === 2)
    return (
      <span className="badge-silver text-[10px] font-bold px-2 py-0.5 rounded-full">
        #2
      </span>
    );
  if (rank === 3)
    return (
      <span className="badge-bronze text-[10px] font-bold px-2 py-0.5 rounded-full">
        #3
      </span>
    );
  return (
    <span className="text-[10px] font-mono text-muted/60 w-6 text-center">
      #{rank}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function CategoryDetailPage() {
  const params = useParams();
  const slug = params?.slug as string;

  const [data, setData] = useState<CategoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  const fetchData = useCallback(
    (serviceType: string, offset: number) => {
      if (!slug) return;
      setLoading(true);
      const typeParam =
        serviceType !== "all" ? `&service_type=${serviceType}` : "";
      fetch(
        `${API_BASE}/v1/categories/${slug}?source=all&limit=${PAGE_SIZE}&offset=${offset}${typeParam}`
      )
        .then((r) => {
          if (!r.ok) throw new Error("Category not found");
          return r.json();
        })
        .then((d) => {
          setData(d);
          setError(null);
        })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    },
    [slug]
  );

  useEffect(() => {
    fetchData(typeFilter, page * PAGE_SIZE);
  }, [fetchData, typeFilter, page]);

  // Update document title client-side
  useEffect(() => {
    if (data) {
      document.title = `Best ${data.label} MCP Servers & AI Tools — Ranked by AEO Score | Clarvia`;

      // Update meta description
      const metaDesc = document.querySelector('meta[name="description"]');
      if (metaDesc) {
        metaDesc.setAttribute(
          "content",
          `Compare ${data.total.toLocaleString()} ${data.label.toLowerCase()} tools ranked by AEO score. Average score: ${data.avg_score}/100. Find the best ${data.label.toLowerCase()} tools for AI agents.`
        );
      }

      // Inject JSON-LD structured data
      const existingJsonLd = document.querySelector(
        'script[data-category-jsonld]'
      );
      if (existingJsonLd) existingJsonLd.remove();

      const jsonLdScript = document.createElement("script");
      jsonLdScript.type = "application/ld+json";
      jsonLdScript.setAttribute("data-category-jsonld", "true");
      jsonLdScript.textContent = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        name: `Best ${data.label} Tools for AI Agents`,
        description: data.description,
        url: `https://clarvia.art/categories/${slug}`,
        numberOfItems: data.total,
        provider: {
          "@type": "Organization",
          name: "Clarvia",
          url: "https://clarvia.art",
        },
        mainEntity: {
          "@type": "ItemList",
          numberOfItems: Math.min(data.tools.length, 10),
          itemListElement: data.tools.slice(0, 10).map((tool, i) => ({
            "@type": "ListItem",
            position: i + 1,
            item: {
              "@type": "SoftwareApplication",
              name: tool.name,
              url: tool.url,
              applicationCategory: data.label,
              description: tool.description || `${tool.name} — AEO Score: ${tool.clarvia_score}/100`,
              aggregateRating: {
                "@type": "AggregateRating",
                ratingValue: tool.clarvia_score,
                bestRating: 100,
                worstRating: 0,
                ratingCount: 1,
              },
            },
          })),
        },
      });
      document.head.appendChild(jsonLdScript);

      // Inject FAQ structured data
      const existingFaqLd = document.querySelector(
        'script[data-faq-jsonld]'
      );
      if (existingFaqLd) existingFaqLd.remove();

      const faqs = generateFAQs(data.label, data.total, data.avg_score);
      const faqScript = document.createElement("script");
      faqScript.type = "application/ld+json";
      faqScript.setAttribute("data-faq-jsonld", "true");
      faqScript.textContent = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: faqs.map((faq) => ({
          "@type": "Question",
          name: faq.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: faq.answer,
          },
        })),
      });
      document.head.appendChild(faqScript);
    }
  }, [data, slug]);

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-mesh flex items-center justify-center">
        <div className="glass-card rounded-2xl p-12 text-center max-w-md">
          <h1 className="text-2xl font-bold mb-4">Category Not Found</h1>
          <p className="text-muted mb-6">
            The category &ldquo;{slug}&rdquo; does not exist.
          </p>
          <Link
            href="/categories"
            className="btn-gradient px-6 py-3 rounded-lg text-sm font-medium inline-block"
          >
            Browse All Categories
          </Link>
        </div>
      </div>
    );
  }

  const faqs = data
    ? generateFAQs(data.label, data.total, data.avg_score)
    : [];
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="min-h-screen bg-gradient-mesh">
      {/* Navigation */}
      <nav className="border-b border-card-border/50 backdrop-blur-md bg-background/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Clarvia"
              width={30}
              height={30}
              className="transition-transform group-hover:scale-110"
            />
            <span className="text-lg font-semibold tracking-tight">
              Clarvia
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <Link
              href="/tools"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Tools
            </Link>
            <Link
              href="/leaderboard"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Leaderboard
            </Link>
            <Link
              href="/guide"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Guide
            </Link>
            <Link
              href="/register"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Register
            </Link>
            <Link
              href="/trending"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Trending
            </Link>
            <Link
              href="/compare"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Compare
            </Link>
            <Link
              href="/docs"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Docs
            </Link>
          </div>
        </div>
      </nav>

      {/* Breadcrumbs */}
      <div className="max-w-7xl mx-auto px-6 pt-6">
        <nav className="text-sm text-muted flex items-center gap-2">
          <Link href="/" className="hover:text-foreground transition-colors">
            Home
          </Link>
          <span>/</span>
          <Link
            href="/categories"
            className="hover:text-foreground transition-colors"
          >
            Categories
          </Link>
          <span>/</span>
          <span className="text-foreground">{data?.label || slug}</span>
        </nav>
      </div>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 pt-8 pb-6">
        {loading && !data ? (
          <div className="animate-pulse">
            <div className="h-10 bg-card-border/30 rounded w-2/3 mb-4" />
            <div className="h-5 bg-card-border/20 rounded w-full mb-6" />
            <div className="flex gap-4">
              <div className="h-20 bg-card-border/20 rounded-xl w-40" />
              <div className="h-20 bg-card-border/20 rounded-xl w-40" />
              <div className="h-20 bg-card-border/20 rounded-xl w-40" />
            </div>
          </div>
        ) : data ? (
          <>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3">
              Best {data.label} MCP Servers & AI Tools{" "}
              <span className="text-muted font-normal text-lg sm:text-xl">
                — Ranked by AEO Score
              </span>
            </h1>
            <p className="text-muted text-lg leading-relaxed mb-8 max-w-3xl">
              {data.description}
            </p>

            {/* Stats */}
            <div className="flex flex-wrap gap-4 mb-8">
              <div className="glass-card rounded-xl px-5 py-3">
                <div className="text-2xl font-bold text-accent">
                  {data.total.toLocaleString()}
                </div>
                <div className="text-xs text-muted">Total Tools</div>
              </div>
              <div className="glass-card rounded-xl px-5 py-3">
                <div
                  className={`text-2xl font-bold ${scoreColor(data.avg_score)}`}
                >
                  {data.avg_score}
                </div>
                <div className="text-xs text-muted">Avg AEO Score</div>
              </div>
              <div className="glass-card rounded-xl px-5 py-3">
                <div className="text-2xl font-bold text-score-green">
                  {data.max_score}
                </div>
                <div className="text-xs text-muted">Top Score</div>
              </div>
              {Object.entries(data.by_type)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 3)
                .map(([type, count]) => (
                  <div key={type} className="glass-card rounded-xl px-5 py-3">
                    <div className="text-2xl font-bold">
                      {count.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted">
                      {(TYPE_LABELS[type] || TYPE_LABELS.general).label}
                    </div>
                  </div>
                ))}
            </div>
          </>
        ) : null}
      </section>

      {/* Filter Tabs + Tool List */}
      <section className="max-w-7xl mx-auto px-6 pb-12">
        {/* Service type filter */}
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
          {SERVICE_TYPE_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setTypeFilter(tab.id);
                setPage(0);
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap cursor-pointer ${
                typeFilter === tab.id
                  ? "btn-gradient"
                  : "glass-subtle text-muted hover:text-foreground"
              }`}
            >
              {tab.label}
              {data?.by_type[tab.id] !== undefined && tab.id !== "all" && (
                <span className="ml-1.5 text-xs opacity-60">
                  ({data.by_type[tab.id]})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tool list */}
        {loading && !data ? (
          <div className="space-y-3">
            {Array.from({ length: 10 }).map((_, i) => (
              <div
                key={i}
                className="glass-card rounded-xl p-4 animate-pulse flex items-center gap-4"
              >
                <div className="w-8 h-8 bg-card-border/30 rounded-lg" />
                <div className="flex-1">
                  <div className="h-4 bg-card-border/30 rounded w-1/3 mb-2" />
                  <div className="h-3 bg-card-border/20 rounded w-2/3" />
                </div>
                <div className="h-8 w-12 bg-card-border/30 rounded" />
              </div>
            ))}
          </div>
        ) : data && data.tools.length > 0 ? (
          <>
            <div className="space-y-2">
              {data.tools.map((tool, i) => {
                const rank = page * PAGE_SIZE + i + 1;
                const rowClass =
                  rank === 1
                    ? "rank-gold-row"
                    : rank === 2
                    ? "rank-silver-row"
                    : rank === 3
                    ? "rank-bronze-row"
                    : "";
                return (
                  <Link
                    key={tool.scan_id}
                    href={`/tool/${tool.scan_id}`}
                    className={`glass-card rounded-xl p-4 flex items-center gap-4 group hover:border-accent/30 transition-all ${rowClass}`}
                  >
                    <div className="flex items-center gap-3 w-12 justify-center flex-shrink-0">
                      <RankBadge rank={rank} />
                    </div>
                    <ServiceIcon url={tool.url} name={tool.name} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-sm group-hover:text-accent transition-colors truncate">
                          {tool.name}
                        </span>
                        <TypeBadge type={tool.service_type} />
                      </div>
                      {tool.description && (
                        <p className="text-xs text-muted truncate max-w-xl">
                          {tool.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-4 flex-shrink-0">
                      {/* Dimension mini-bars */}
                      <div className="hidden sm:flex items-center gap-1.5">
                        {["api_accessibility", "data_structuring", "agent_compatibility", "trust_signals"].map(
                          (dim) => {
                            const val = tool.dimensions?.[dim] ?? 0;
                            const maxVal = dim === "trust_signals" ? 15 : 30;
                            const pct = Math.round((val / maxVal) * 100);
                            return (
                              <div
                                key={dim}
                                className="w-8 h-1.5 bg-card-border/30 rounded-full overflow-hidden"
                                title={`${dim.replace("_", " ")}: ${val}/${maxVal}`}
                              >
                                <div
                                  className={`h-full rounded-full ${
                                    pct >= 70
                                      ? "bar-gradient-green"
                                      : pct >= 40
                                      ? "bar-gradient-yellow"
                                      : "bar-gradient-red"
                                  }`}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            );
                          }
                        )}
                      </div>
                      <div
                        className={`text-xl font-bold font-mono min-w-[3ch] text-right ${scoreColor(
                          tool.clarvia_score
                        )}`}
                      >
                        {tool.clarvia_score}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="glass-subtle px-4 py-2 rounded-lg text-sm disabled:opacity-30 cursor-pointer"
                >
                  Previous
                </button>
                <span className="text-sm text-muted px-4">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="glass-subtle px-4 py-2 rounded-lg text-sm disabled:opacity-30 cursor-pointer"
                >
                  Next
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="glass-card rounded-xl p-12 text-center">
            <p className="text-muted">
              No tools found in this category with the selected filter.
            </p>
          </div>
        )}
      </section>

      {/* FAQ Section */}
      {data && faqs.length > 0 && (
        <section className="max-w-4xl mx-auto px-6 pb-16">
          <h2 className="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
          <div className="space-y-4">
            {faqs.map((faq, i) => (
              <details
                key={i}
                className="glass-card rounded-xl group"
                open={i === 0}
              >
                <summary className="px-6 py-4 cursor-pointer text-sm font-semibold flex items-center justify-between list-none">
                  <span>{faq.question}</span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="text-muted flex-shrink-0 ml-4 transition-transform group-open:rotate-180"
                  >
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </summary>
                <div className="px-6 pb-4 text-sm text-muted leading-relaxed">
                  {faq.answer}
                </div>
              </details>
            ))}
          </div>
        </section>
      )}

      {/* Related Categories */}
      {data && (
        <section className="max-w-7xl mx-auto px-6 pb-16">
          <h2 className="text-xl font-bold mb-4">Browse Other Categories</h2>
          <div className="flex flex-wrap gap-2">
            {[
              "ai",
              "developer_tools",
              "database",
              "communication",
              "cloud",
              "data",
              "productivity",
              "search",
              "monitoring",
              "testing",
              "security",
              "payments",
              "automation",
              "storage",
              "analytics",
              "cms",
              "design",
              "documentation",
              "blockchain",
              "media",
            ]
              .filter((s) => s !== slug)
              .slice(0, 12)
              .map((s) => (
                <Link
                  key={s}
                  href={`/categories/${s}`}
                  className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:text-accent hover:border-accent/30 transition-colors"
                >
                  {s.replace("_", " ")}
                </Link>
              ))}
            <Link
              href="/categories"
              className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono text-accent hover:border-accent/30 transition-colors"
            >
              View all categories
            </Link>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="border-t border-card-border/30 py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted">
            Clarvia indexes and scores AI agent tools using the AEO standard.
          </p>
          <div className="flex items-center gap-6">
            <Link
              href="/about"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              About
            </Link>
            <Link
              href="/methodology"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Methodology
            </Link>
            <Link
              href="/scan"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Scan Your Tool
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
