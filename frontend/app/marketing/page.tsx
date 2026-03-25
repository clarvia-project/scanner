"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

// Admin key is passed via URL query param (?key=...) and forwarded to
// the backend which validates it via X-API-Key header. No secret stored
// in frontend code — the backend is the single source of truth.
const ADMIN_KEY_PARAM = "key";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface KpiData {
  generated_at: string;
  kpi: {
    total_scans: number;
    total_tools: number;
    cached_scans: number;
    avg_score: number;
    badge_requests: number;
  };
  placeholders: {
    mcp_server_installs: number | null;
    ai_search_citations: number | null;
    compare_card_shares: number | null;
    llms_txt_hits: number | null;
  };
  score_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  type_distribution: Record<string, number>;
  recent_services: {
    name: string;
    scan_id: string;
    score: number;
    category: string;
    scanned_at: string | null;
  }[];
  channels: { name: string; done: boolean }[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORY_COLORS: Record<string, string> = {
  ai: "#818cf8",
  developer_tools: "#34d399",
  communication: "#f472b6",
  data: "#fbbf24",
  productivity: "#a78bfa",
  blockchain: "#22d3ee",
  payments: "#fb923c",
  mcp: "#60a5fa",
  other: "#6b7280",
};

const CATEGORY_LABELS: Record<string, string> = {
  ai: "AI / ML",
  developer_tools: "Dev Tools",
  communication: "Communication",
  data: "Data",
  productivity: "Productivity",
  blockchain: "Blockchain",
  payments: "Payments",
  mcp: "MCP",
  other: "Other",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function MarketingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" /></div>}>
      <MarketingContent />
    </Suspense>
  );
}

function MarketingContent() {
  const searchParams = useSearchParams();
  const [data, setData] = useState<KpiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const adminKey = searchParams.get(ADMIN_KEY_PARAM) ?? "";
  const hasKey = adminKey.length > 0;

  useEffect(() => {
    if (!hasKey) return;
    fetch(`${API_BASE}/v1/marketing/kpi`, {
      headers: { "X-API-Key": adminKey },
    })
      .then((r) => {
        if (r.status === 401 || r.status === 403) throw new Error("Invalid admin key");
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [hasKey, adminKey]);

  if (!hasKey) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card rounded-xl p-8 text-center max-w-sm">
          <p className="text-muted text-sm">Admin access required</p>
          <p className="text-[10px] text-muted/40 font-mono mt-2">/marketing?key=***</p>
        </div>
      </div>
    );
  }

  // Compute max for bar chart scaling
  const catMax =
    data && data.category_distribution
      ? Math.max(...Object.values(data.category_distribution), 1)
      : 1;

  const channelsDone = data?.channels.filter((c) => c.done).length ?? 0;
  const channelsTotal = data?.channels.length ?? 0;

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
              <Link href="/trending" className="text-sm text-muted hover:text-foreground transition-colors">Trending</Link>
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">Leaderboard</Link>
              <Link href="/marketing" className="text-sm text-foreground font-medium">Marketing</Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">Docs</Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Hero */}
        <div className="mb-8 space-y-3">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Marketing KPI Dashboard</h1>
            <span className="text-[10px] font-mono px-2 py-1 rounded-full bg-accent/10 text-accent border border-accent/20">
              INTERNAL
            </span>
          </div>
          <p className="text-muted max-w-2xl">
            Clarvia AEO 마케팅 지표 현황. 실시간 데이터 + 연동 예정 placeholder.
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="glass-card rounded-xl p-6 h-32 animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="glass-card rounded-xl p-12 text-center">
            <p className="text-red-400 font-mono text-sm">Error: {error}</p>
          </div>
        ) : data ? (
          <>
            {/* ==================== KPI Cards ==================== */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
              <KpiCard
                label="Total Scans"
                value={data.kpi.total_scans}
                sub={`avg score ${data.kpi.avg_score}`}
                accent="#818cf8"
              />
              <KpiCard
                label="Total Tools"
                value={data.kpi.total_tools}
                sub="services + collected"
                accent="#34d399"
              />
              <KpiCard
                label="Badge Requests"
                value={data.kpi.badge_requests}
                sub="embed badge served"
                accent="#fbbf24"
              />
              <KpiCard
                label="AI Citations"
                value={data.placeholders.ai_search_citations}
                sub="placeholder - TBD"
                accent="#f472b6"
                placeholder
              />
            </div>

            {/* ==================== Category Distribution ==================== */}
            <section className="mb-10">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                Category Distribution
              </h2>
              <div className="glass-card rounded-xl p-6 space-y-3">
                {Object.entries(data.category_distribution)
                  .sort((a, b) => b[1] - a[1])
                  .map(([cat, count]) => {
                    const pct = Math.round((count / catMax) * 100);
                    const color = CATEGORY_COLORS[cat] || CATEGORY_COLORS.other;
                    return (
                      <div key={cat} className="flex items-center gap-3">
                        <span className="text-xs font-mono text-muted w-28 text-right shrink-0">
                          {CATEGORY_LABELS[cat] || cat}
                        </span>
                        <div className="flex-1 h-6 rounded bg-card-border/20 overflow-hidden relative">
                          <div
                            className="h-full rounded transition-all duration-700"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: color,
                              opacity: 0.7,
                            }}
                          />
                          <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-mono font-bold text-foreground/80">
                            {count}
                          </span>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </section>

            {/* ==================== Service Type Distribution ==================== */}
            <section className="mb-10">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                Service Type Breakdown
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {Object.entries(data.type_distribution)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, count]) => (
                    <div key={type} className="glass-card rounded-xl p-4 text-center">
                      <div className="text-2xl font-bold font-mono text-foreground">
                        {count.toLocaleString()}
                      </div>
                      <div className="text-[10px] font-mono text-muted mt-1 uppercase">
                        {type.replace("_", " ")}
                      </div>
                    </div>
                  ))}
              </div>
            </section>

            {/* ==================== Bottom: Activity + Channels ==================== */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Activity */}
              <section>
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  Recent Scans
                </h2>
                <div className="glass-card rounded-xl divide-y divide-card-border/30">
                  {data.recent_services.length === 0 ? (
                    <div className="p-6 text-center text-muted text-sm">No recent scans</div>
                  ) : (
                    data.recent_services.map((svc) => (
                      <Link
                        key={svc.scan_id}
                        href={`/scan/${svc.scan_id}`}
                        className="flex items-center justify-between px-4 py-3 hover:bg-card-border/10 transition-colors group"
                      >
                        <div className="min-w-0">
                          <span className="text-sm font-medium truncate block group-hover:text-accent transition-colors">
                            {svc.name}
                          </span>
                          <span className="text-[10px] font-mono text-muted">
                            {svc.category} &middot;{" "}
                            {svc.scanned_at
                              ? new Date(svc.scanned_at).toLocaleDateString()
                              : "N/A"}
                          </span>
                        </div>
                        <span
                          className={`text-sm font-bold font-mono ${
                            svc.score >= 70
                              ? "text-score-green"
                              : svc.score >= 40
                              ? "text-score-yellow"
                              : "text-score-red"
                          }`}
                        >
                          {svc.score}
                        </span>
                      </Link>
                    ))
                  )}
                </div>
              </section>

              {/* Marketing Channel Checklist */}
              <section>
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Marketing Channels
                  <span className="text-[10px] font-mono text-muted ml-auto">
                    {channelsDone}/{channelsTotal}
                  </span>
                </h2>
                <div className="glass-card rounded-xl p-4 space-y-1">
                  {/* Progress bar */}
                  <div className="h-2 rounded-full bg-card-border/30 mb-4 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-emerald-500 transition-all duration-700"
                      style={{
                        width: `${Math.round((channelsDone / Math.max(channelsTotal, 1)) * 100)}%`,
                      }}
                    />
                  </div>
                  {data.channels.map((ch) => (
                    <label
                      key={ch.name}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                        ch.done ? "text-foreground/80" : "text-muted"
                      }`}
                    >
                      <span
                        className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                          ch.done
                            ? "bg-emerald-500/20 border-emerald-500/50"
                            : "border-card-border/50"
                        }`}
                      >
                        {ch.done && (
                          <svg
                            className="w-2.5 h-2.5 text-emerald-400"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={3}
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </span>
                      <span className={ch.done ? "" : "opacity-60"}>{ch.name}</span>
                    </label>
                  ))}
                </div>
              </section>
            </div>

            {/* ==================== Placeholder KPIs ==================== */}
            <section className="mt-10">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Pending Integrations
                <span className="text-[10px] font-mono text-muted/50 ml-2">
                  data source TBD
                </span>
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <PlaceholderCard label="MCP Server Installs" detail="npm downloads" />
                <PlaceholderCard label="AI Search Citations" detail="Perplexity / ChatGPT" />
                <PlaceholderCard label="Compare Card Shares" detail="social shares" />
                <PlaceholderCard label="llms.txt Hits" detail="access log count" />
              </div>
            </section>

            {/* Footer timestamp */}
            <div className="mt-8 text-center text-[10px] font-mono text-muted/40">
              Generated: {new Date(data.generated_at).toLocaleString()}
            </div>
          </>
        ) : null}
      </main>

      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia -- The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KpiCard({
  label,
  value,
  sub,
  accent,
  placeholder = false,
}: {
  label: string;
  value: number | null;
  sub: string;
  accent: string;
  placeholder?: boolean;
}) {
  return (
    <div className="glass-card rounded-xl p-6 relative overflow-hidden">
      {/* Accent bar */}
      <div
        className="absolute top-0 left-0 w-full h-0.5"
        style={{ backgroundColor: accent, opacity: 0.6 }}
      />
      <div className="text-xs font-mono text-muted mb-2 uppercase tracking-wider">
        {label}
      </div>
      <div className="text-3xl font-bold font-mono text-foreground">
        {placeholder || value === null ? (
          <span className="text-muted/30">--</span>
        ) : (
          value.toLocaleString()
        )}
      </div>
      <div className="text-[10px] font-mono text-muted/60 mt-1">{sub}</div>
    </div>
  );
}

function PlaceholderCard({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="glass-card rounded-xl p-5 border-dashed border-card-border/30 opacity-50">
      <div className="text-xs font-mono text-muted mb-1">{label}</div>
      <div className="text-2xl font-bold font-mono text-muted/30">--</div>
      <div className="text-[10px] font-mono text-muted/40 mt-1">{detail}</div>
    </div>
  );
}
