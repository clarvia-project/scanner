"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

interface Tool {
  name: string;
  url: string;
  category: string;
  service_type: string;
  clarvia_score: number;
  rating: string;
  scan_id: string;
  description?: string;
  connection_info?: Record<string, unknown>;
}

interface Stats {
  total_services: number;
  by_type: Record<string, number>;
  scanned_count?: number;
  collected_count?: number;
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  mcp_server: { label: "MCP", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  api: { label: "API", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  cli_tool: { label: "CLI", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  skill: { label: "Skill", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  general: { label: "General", color: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
};

const CATEGORIES = [
  { key: "", label: "All" },
  { key: "ai", label: "AI / ML" },
  { key: "developer_tools", label: "Dev Tools" },
  { key: "communication", label: "Communication" },
  { key: "data", label: "Data" },
  { key: "productivity", label: "Productivity" },
  { key: "blockchain", label: "Blockchain" },
  { key: "payments", label: "Payments" },
  { key: "other", label: "Other" },
];

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function TypeBadge({ type }: { type: string }) {
  const info = TYPE_LABELS[type] || TYPE_LABELS.general;
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${info.color}`}>
      {info.label}
    </span>
  );
}

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [category, setCategory] = useState("");
  const [sortOrder, setSortOrder] = useState("score_desc");
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 30;

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(t);
  }, [query]);

  // Reset offset when filters change
  useEffect(() => {
    setOffset(0);
  }, [debouncedQuery, serviceType, category, sortOrder]);

  // Fetch stats
  useEffect(() => {
    fetch(`${API_BASE}/v1/stats?source=all`)
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
  }, []);

  // Fetch tools
  const fetchTools = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams({
      source: "all",
      limit: String(limit),
      offset: String(offset),
      sort: sortOrder,
    });
    if (debouncedQuery) params.set("q", debouncedQuery);
    if (serviceType) params.set("service_type", serviceType);
    if (category) params.set("category", category);

    try {
      const res = await fetch(`${API_BASE}/v1/services?${params}`);
      const data = await res.json();
      setTools(data.services || []);
      setTotal(data.total || 0);
    } catch {
      setTools([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery, serviceType, category, sortOrder, offset]);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  const handleExportCSV = async () => {
    const params = new URLSearchParams({
      source: "all",
      limit: "1000",
      offset: "0",
      sort: sortOrder,
    });
    if (debouncedQuery) params.set("q", debouncedQuery);
    if (serviceType) params.set("service_type", serviceType);
    if (category) params.set("category", category);

    try {
      const res = await fetch(`${API_BASE}/v1/services?${params}`);
      const data = await res.json();
      const rows = (data.services || []).map((t: Tool) =>
        [t.name, t.service_type, t.category, t.clarvia_score, t.rating, t.url, t.description || ""].map(
          (v) => `"${String(v).replace(/"/g, '""')}"`
        ).join(",")
      );
      const csv = ["Name,Type,Category,Score,Rating,URL,Description", ...rows].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `clarvia-tools-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* ignore */ }
  };

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
              <Link href="/tools" className="text-sm text-foreground font-medium">
                Tools
              </Link>
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">
                Leaderboard
              </Link>
              <Link href="/register" className="text-sm text-muted hover:text-foreground transition-colors">
                Register
              </Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">
                Docs
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Hero */}
        <div className="mb-8 space-y-3">
          <h1 className="text-3xl font-bold tracking-tight">
            Agent Tool Directory
          </h1>
          <p className="text-muted max-w-2xl">
            Search{" "}
            <span className="text-foreground font-semibold font-mono">
              {stats?.total_services?.toLocaleString() || "12,000+"}
            </span>{" "}
            tools across MCP servers, APIs, CLI tools, and skills.
            Every tool scored for agent readiness.
          </p>
        </div>

        {/* Stats bar */}
        {stats && (
          <div className="flex flex-wrap gap-3 mb-6">
            {Object.entries(stats.by_type || {}).map(([type, count]) => {
              const info = TYPE_LABELS[type] || TYPE_LABELS.general;
              return (
                <button
                  key={type}
                  onClick={() => setServiceType(serviceType === type ? "" : type)}
                  className={`glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono flex items-center gap-2 transition-all cursor-pointer ${
                    serviceType === type ? "ring-1 ring-accent" : ""
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${info.color.split(" ")[0]}`} />
                  {info.label}
                  <span className="text-muted">{count.toLocaleString()}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Search + Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex-1 relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search tools... (e.g. github, slack, database)"
              className="w-full glass-subtle pl-10 pr-4 py-2.5 rounded-lg text-sm placeholder:text-muted/50 focus:outline-none"
            />
          </div>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="glass-subtle px-3 py-2.5 rounded-lg text-sm bg-transparent cursor-pointer focus:outline-none"
          >
            {CATEGORIES.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            className="glass-subtle px-3 py-2.5 rounded-lg text-sm bg-transparent cursor-pointer focus:outline-none"
          >
            <option value="score_desc">Score ↓</option>
            <option value="score_asc">Score ↑</option>
            <option value="name_asc">Name A-Z</option>
            <option value="recent">Recent</option>
          </select>
        </div>

        {/* Results count */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <p className="text-xs text-muted font-mono">
              {total.toLocaleString()} results
              {debouncedQuery && ` for "${debouncedQuery}"`}
            </p>
            <button
              onClick={handleExportCSV}
              className="text-[10px] text-muted/60 hover:text-accent font-mono px-2 py-1 rounded border border-card-border/30 hover:border-accent/30 transition-all"
            >
              CSV ↓
            </button>
          </div>
          {totalPages > 1 && (
            <p className="text-xs text-muted font-mono">
              Page {currentPage} / {totalPages}
            </p>
          )}
        </div>

        {/* Tool Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="glass-card rounded-xl p-4 h-32 animate-pulse" />
            ))}
          </div>
        ) : tools.length === 0 ? (
          <div className="glass-card rounded-xl p-12 text-center">
            <p className="text-muted">No tools found. Try a different search.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {tools.map((tool) => (
              <Link
                key={tool.scan_id}
                href={
                  tool.scan_id.startsWith("tool_")
                    ? `/tool/${tool.scan_id}`
                    : `/scan/${tool.scan_id}`
                }
                className="glass-card rounded-xl p-4 hover:border-accent/30 transition-all group flex flex-col"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <TypeBadge type={tool.service_type} />
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
                  <p className="text-xs text-muted/70 line-clamp-2 mb-1.5 leading-relaxed">
                    {tool.description}
                  </p>
                )}
                {tool.url && !tool.description && (
                  <p className="text-[11px] text-muted/60 font-mono truncate mb-1.5">
                    {tool.url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                  </p>
                )}
                <div className="flex items-center gap-2 mt-auto">
                  <span className="text-[10px] text-muted/50 font-mono px-1.5 py-0.5 rounded bg-card-border/30">
                    {tool.category}
                  </span>
                  <span className={`text-[10px] font-mono ${scoreColor(tool.clarvia_score)}/60`}>
                    {tool.rating}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="glass-subtle px-4 py-2 rounded-lg text-sm disabled:opacity-30 cursor-pointer"
            >
              Prev
            </button>
            {/* Page numbers */}
            {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
              let page: number;
              if (totalPages <= 5) {
                page = i + 1;
              } else if (currentPage <= 3) {
                page = i + 1;
              } else if (currentPage >= totalPages - 2) {
                page = totalPages - 4 + i;
              } else {
                page = currentPage - 2 + i;
              }
              return (
                <button
                  key={page}
                  onClick={() => setOffset((page - 1) * limit)}
                  className={`w-9 h-9 rounded-lg text-sm font-mono cursor-pointer ${
                    page === currentPage
                      ? "btn-gradient text-white"
                      : "glass-subtle"
                  }`}
                >
                  {page}
                </button>
              );
            })}
            <button
              onClick={() => setOffset(Math.min((totalPages - 1) * limit, offset + limit))}
              disabled={currentPage >= totalPages}
              className="glass-subtle px-4 py-2 rounded-lg text-sm disabled:opacity-30 cursor-pointer"
            >
              Next
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia — The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}
