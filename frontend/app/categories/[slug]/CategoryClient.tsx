"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Tool {
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

export interface CategoryData {
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
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
// Main Client Component (handles filtering + pagination only)
// ---------------------------------------------------------------------------

interface CategoryClientProps {
  initialData: CategoryData;
  slug: string;
  faqs: { question: string; answer: string }[];
}

export default function CategoryClient({
  initialData,
  slug,
  faqs,
}: CategoryClientProps) {
  const [data, setData] = useState<CategoryData>(initialData);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState("all");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  const fetchData = useCallback(
    (serviceType: string, offset: number) => {
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
        .then((d) => setData(d))
        .catch(console.warn)
        .finally(() => setLoading(false));
    },
    [slug]
  );

  const handleTypeFilter = (newType: string) => {
    setTypeFilter(newType);
    setPage(0);
    fetchData(newType, 0);
  };

  const handlePage = (newPage: number) => {
    setPage(newPage);
    fetchData(typeFilter, newPage * PAGE_SIZE);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const totalPages = Math.ceil(data.total / PAGE_SIZE);

  return (
    <>
      {/* Filter Tabs + Tool List */}
      <section className="max-w-7xl mx-auto px-6 pb-12">
        {/* Service type filter */}
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
          {SERVICE_TYPE_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTypeFilter(tab.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap cursor-pointer ${
                typeFilter === tab.id
                  ? "btn-gradient"
                  : "glass-subtle text-muted hover:text-foreground"
              }`}
            >
              {tab.label}
              {data.by_type[tab.id] !== undefined && tab.id !== "all" && (
                <span className="ml-1.5 text-xs opacity-60">
                  ({data.by_type[tab.id]})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tool list */}
        {loading ? (
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
        ) : data.tools.length > 0 ? (
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
                      <div className="hidden sm:flex items-center gap-1.5">
                        {[
                          "api_accessibility",
                          "data_structuring",
                          "agent_compatibility",
                          "trust_signals",
                        ].map((dim) => {
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
                        })}
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
                  onClick={() => handlePage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="glass-subtle px-4 py-2 rounded-lg text-sm disabled:opacity-30 cursor-pointer"
                >
                  Previous
                </button>
                <span className="text-sm text-muted px-4">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => handlePage(Math.min(totalPages - 1, page + 1))}
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
      {faqs.length > 0 && (
        <section className="max-w-4xl mx-auto px-6 pb-16">
          <h2 className="text-2xl font-bold mb-6">
            Frequently Asked Questions
          </h2>
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
    </>
  );
}
