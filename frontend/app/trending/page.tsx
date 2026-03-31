"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

interface TrendingTool {
  name: string;
  scan_id: string;
  url: string;
  description: string;
  category: string;
  service_type: string;
  clarvia_score: number;
  rating: string;
}

interface CategoryStat {
  count: number;
  avg_score: number;
  top_score: number;
}

interface TrendingData {
  top_tools: TrendingTool[];
  by_category: Record<string, TrendingTool[]>;
  rising_stars: TrendingTool[];
  service_type_leaders: Record<string, TrendingTool>;
  category_stats: Record<string, CategoryStat>;
  total_indexed: number;
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  mcp_server: { label: "MCP", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  api: { label: "API", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  cli_tool: { label: "CLI", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  skill: { label: "Skill", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  general: { label: "General", color: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
};

const CATEGORY_LABELS: Record<string, { label: string; emoji: string }> = {
  ai: { label: "AI / ML", emoji: "brain" },
  developer_tools: { label: "Dev Tools", emoji: "tools" },
  communication: { label: "Communication", emoji: "chat" },
  data: { label: "Data", emoji: "chart" },
  productivity: { label: "Productivity", emoji: "check" },
  blockchain: { label: "Blockchain", emoji: "link" },
  payments: { label: "Payments", emoji: "card" },
  mcp: { label: "MCP", emoji: "plug" },
  other: { label: "Other", emoji: "box" },
};

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function getFaviconUrl(url: string): string | null {
  if (!url) return null;
  try {
    const domain = new URL(url.startsWith("http") ? url : `https://${url}`).hostname;
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

function ToolCard({ tool, rank }: { tool: TrendingTool; rank?: number }) {
  const typeInfo = TYPE_LABELS[tool.service_type] || TYPE_LABELS.general;
  return (
    <Link
      href={tool.scan_id.startsWith("tool_") ? `/tool/${tool.scan_id}` : `/scan/${tool.scan_id}`}
      className="glass-card rounded-xl p-4 hover:border-accent/30 transition-all group flex flex-col"
    >
      <div className="flex items-start gap-3 mb-2">
        {rank !== undefined && (
          <span className="text-lg font-bold text-muted/30 font-mono w-6 text-right flex-shrink-0">
            {rank}
          </span>
        )}
        <ServiceIcon url={tool.url} name={tool.name} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${typeInfo.color}`}>
              {typeInfo.label}
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
  );
}

export default function TrendingPage() {
  const [data, setData] = useState<TrendingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/v1/trending?limit=20`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-card-border/50 backdrop-blur-xl bg-background/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
              <Image
                src="/logos/clarvia-icon.svg"
                alt="Clarvia"
                width={30}
                height={30}
                className="group-hover:scale-110 transition-transform duration-200"
                unoptimized
              />
              <span className="font-semibold text-base tracking-tight text-foreground">
                clarvia
              </span>
            </Link>
            <nav className="hidden sm:flex items-center gap-6">
              <Link href="/tools" className="text-sm text-muted hover:text-foreground transition-colors">Tools</Link>
              <Link href="/trending" className="text-sm text-foreground font-medium">Trending</Link>
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">Leaderboard</Link>
              <Link href="/compare" className="text-sm text-muted hover:text-foreground transition-colors">Compare</Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">Docs</Link>
            </nav>
          </div>
        </div>
      </header>

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
              {data?.total_indexed?.toLocaleString() || "..."}
            </span>{" "}
            indexed services. Updated weekly.
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="glass-card rounded-xl p-4 h-32 animate-pulse" />
            ))}
          </div>
        ) : data ? (
          <>
            {/* Category Stats Bar */}
            <div className="flex flex-wrap gap-2 mb-8">
              {Object.entries(data.category_stats || {})
                .sort((a, b) => {
                  if (a[0] === "other") return 1;
                  if (b[0] === "other") return -1;
                  return b[1].count - a[1].count;
                })
                .map(([cat, stats]) => {
                  const info = CATEGORY_LABELS[cat] || CATEGORY_LABELS.other;
                  return (
                    <button
                      key={cat}
                      onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
                      className={`glass-subtle px-3 py-2 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-2 ${
                        activeCategory === cat ? "ring-1 ring-accent border-accent/30" : ""
                      }`}
                    >
                      <span className="text-foreground font-semibold">{info.label}</span>
                      <span className="text-muted/50">{stats.count}</span>
                      <span className={`font-bold ${scoreColor(stats.avg_score)}`}>
                        avg {stats.avg_score}
                      </span>
                    </button>
                  );
                })}
            </div>

            {/* Service Type Leaders */}
            {data.service_type_leaders && Object.keys(data.service_type_leaders).length > 0 ? (
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
            ) : null}

            {/* Top Tools or Category View */}
            <section className="mb-10">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                {activeCategory
                  ? `Top ${CATEGORY_LABELS[activeCategory]?.label || activeCategory}`
                  : "Top Tools Overall"}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {(activeCategory && data.by_category?.[activeCategory]
                  ? data.by_category[activeCategory]
                  : data.top_tools || []
                ).map((tool, idx) => (
                  <ToolCard key={tool.scan_id} tool={tool} rank={idx + 1} />
                ))}
              </div>
            </section>

            {/* Rising Stars */}
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
                    <ToolCard key={tool.scan_id} tool={tool} />
                  ))}
                </div>
              </section>
            )}
          </>
        ) : (
          <div className="glass-card rounded-xl p-12 text-center">
            <p className="text-muted">Failed to load trending data.</p>
          </div>
        )}
      </main>

      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia — The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}
