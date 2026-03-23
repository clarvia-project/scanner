"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

// ----- Types -----

interface Dimension {
  score: number;
  max: number;
}

interface ScanEntry {
  scan_id: string;
  url: string;
  service_name: string;
  clarvia_score: number;
  rating: string;
  scanned_at: string;
  dimensions: {
    api_accessibility: Dimension;
    data_structuring: Dimension;
    agent_compatibility: Dimension;
    trust_signals: Dimension;
  };
}

// ----- Category mapping -----

const CATEGORY_MAP: Record<string, string[]> = {
  "AI/LLM": [
    "openai", "anthropic", "google ai", "mistral", "cohere",
    "replicate", "hugging face", "together ai", "groq", "perplexity",
  ],
  "Developer Tools": [
    "github", "gitlab", "vercel", "netlify", "supabase",
    "firebase", "aws", "cloudflare", "railway", "render",
  ],
  Payments: ["stripe", "paypal", "squareup", "plaid", "coinbase", "circle"],
  Communication: ["slack", "discord", "twilio", "sendgrid", "resend"],
  Data: ["snowflake", "databricks", "mixpanel", "amplitude", "segment"],
  Productivity: ["notion", "linear", "atlassian", "asana", "figma", "canva"],
  Blockchain: ["solana", "ethereum", "helius", "alchemy", "moralis", "dune"],
  MCP: ["mcp", "smithery", "glama"],
};

const CATEGORIES = ["All", ...Object.keys(CATEGORY_MAP)];

function getCategory(serviceName: string): string {
  const lower = serviceName.toLowerCase();
  for (const [cat, names] of Object.entries(CATEGORY_MAP)) {
    if (names.some((n) => lower.includes(n))) return cat;
  }
  return "Other";
}

// ----- Helpers -----

function scoreColor(score: number): string {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function ratingBadgeClass(rating: string): string {
  switch (rating) {
    case "Exceptional":
    case "Strong":
      return "bg-score-green/10 text-score-green border border-score-green/20";
    case "Moderate":
    case "Good":
      return "bg-score-yellow/10 text-score-yellow border border-score-yellow/20";
    case "Basic":
      return "bg-score-yellow/10 text-score-yellow border border-score-yellow/20";
    default:
      return "bg-score-red/10 text-score-red border border-score-red/20";
  }
}

function dimBarGradient(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bar-gradient-green";
  if (pct >= 0.4) return "bar-gradient-yellow";
  return "bar-gradient-red";
}

// ----- Components -----

function DimMiniBar({
  label,
  score,
  max,
}: {
  label: string;
  score: number;
  max: number;
}) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  return (
    <div className="flex items-center gap-2 min-w-0">
      <span className="text-[10px] text-muted w-10 shrink-0 text-right font-mono">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-card-border/50 rounded-full overflow-hidden min-w-[40px]">
        <div
          className={`h-full rounded-full ${dimBarGradient(score, max)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-muted font-mono w-8 shrink-0">
        {score}/{max}
      </span>
    </div>
  );
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return <span className="inline-flex items-center justify-center w-7 h-7 rounded-full badge-gold text-[11px] font-bold">1</span>;
  }
  if (rank === 2) {
    return <span className="inline-flex items-center justify-center w-7 h-7 rounded-full badge-silver text-[11px] font-bold">2</span>;
  }
  if (rank === 3) {
    return <span className="inline-flex items-center justify-center w-7 h-7 rounded-full badge-bronze text-[11px] font-bold">3</span>;
  }
  return <span className="text-sm text-muted font-mono">{rank}</span>;
}

// ----- Main Page -----

export default function LeaderboardPage() {
  const [data, setData] = useState<ScanEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("All");
  const [search, setSearch] = useState("");
  const router = useRouter();

  useEffect(() => {
    fetch("/data/prebuilt-scans.json")
      .then((res) => res.json())
      .then((json: ScanEntry[]) => {
        const sorted = [...json].sort(
          (a, b) => b.clarvia_score - a.clarvia_score,
        );
        setData(sorted);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let list = data;

    if (category !== "All") {
      list = list.filter((item) => getCategory(item.service_name) === category);
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (item) =>
          item.service_name.toLowerCase().includes(q) ||
          item.url.toLowerCase().includes(q),
      );
    }

    return list;
  }, [data, category, search]);

  return (
    <div className="flex flex-col min-h-screen bg-gradient-mesh">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-card-border/50 backdrop-blur-xl bg-background/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="w-7 h-7 rounded-lg bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                <div className="w-3 h-3 rounded-sm bg-accent" />
              </div>
              <span className="font-semibold text-base tracking-tight text-foreground">Clarvia</span>
            </Link>
            <nav className="hidden sm:flex items-center gap-6">
              <Link href="/leaderboard" className="text-sm text-foreground font-medium">
                Leaderboard
              </Link>
              <Link href="/register" className="text-sm text-muted hover:text-foreground transition-colors">
                Register
              </Link>
            </nav>
          </div>
          <span className="text-xs text-muted/60 font-mono hidden sm:inline">v1.0</span>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12">
        {/* Title */}
        <div className="text-center space-y-4 mb-12">
          <p className="text-xs font-mono text-accent uppercase tracking-widest">Rankings</p>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            AEO Leaderboard
          </h1>
          <p className="text-muted text-sm md:text-base max-w-xl mx-auto">
            How agent-ready is your favorite service?
          </p>
        </div>

        {/* Search */}
        <div className="mb-8 max-w-md mx-auto">
          <div className="relative">
            <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search services..."
              className="w-full bg-card-bg/80 border border-card-border rounded-xl pl-11 pr-4 py-3 text-foreground placeholder:text-muted/40 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all font-mono text-sm"
            />
          </div>
        </div>

        {/* Category filters */}
        <div className="flex flex-wrap justify-center gap-2 mb-10">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-4 py-2 rounded-xl text-xs font-medium transition-all duration-200 border ${
                category === cat
                  ? "btn-gradient text-white border-transparent shadow-md shadow-accent/10"
                  : "bg-card-bg/60 text-muted border-card-border hover:border-accent/30 hover:text-foreground"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-muted text-sm mb-4">No services found.</p>
            <button
              onClick={() => { setCategory("All"); setSearch(""); }}
              className="text-accent text-sm hover:text-accent-hover transition-colors"
            >
              Clear filters
            </button>
          </div>
        ) : (
          /* Table */
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-card-border/50 text-left text-xs text-muted uppercase tracking-wider">
                    <th className="px-6 py-4 w-10">#</th>
                    <th className="px-4 py-4">Service</th>
                    <th className="px-4 py-4 text-center w-20">Score</th>
                    <th className="px-4 py-4 text-center w-28">Rating</th>
                    <th className="px-4 py-4 hidden lg:table-cell min-w-[280px]">
                      Dimensions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((item, idx) => (
                    <tr
                      key={item.scan_id}
                      onClick={() => router.push(`/scan/${item.scan_id}`)}
                      className={`border-b border-card-border/30 cursor-pointer transition-all duration-200 group ${
                        idx === 0 ? "rank-gold-row hover:bg-yellow-500/5" :
                        idx === 1 ? "rank-silver-row hover:bg-gray-400/5" :
                        idx === 2 ? "rank-bronze-row hover:bg-orange-500/5" :
                        "hover:bg-card-border/10"
                      }`}
                    >
                      {/* Rank */}
                      <td className="px-6 py-4">
                        <RankBadge rank={idx + 1} />
                      </td>

                      {/* Service name + URL */}
                      <td className="px-4 py-4">
                        <div className="font-medium group-hover:text-accent transition-colors">
                          {item.service_name}
                        </div>
                        <div className="text-xs text-muted font-mono truncate max-w-[200px]">
                          {item.url.replace(/^https?:\/\//, "")}
                        </div>
                      </td>

                      {/* Score */}
                      <td className="px-4 py-4 text-center">
                        <span
                          className={`font-mono font-bold text-lg ${scoreColor(item.clarvia_score)}`}
                        >
                          {item.clarvia_score}
                        </span>
                      </td>

                      {/* Rating badge */}
                      <td className="px-4 py-4 text-center">
                        <span
                          className={`inline-block px-2.5 py-1 rounded-lg text-[10px] font-mono uppercase tracking-wider ${ratingBadgeClass(item.rating)}`}
                        >
                          {item.rating}
                        </span>
                      </td>

                      {/* Dimension bars */}
                      <td className="px-4 py-4 hidden lg:table-cell">
                        <div className="space-y-1">
                          <DimMiniBar
                            label="API"
                            score={item.dimensions.api_accessibility.score}
                            max={item.dimensions.api_accessibility.max}
                          />
                          <DimMiniBar
                            label="Data"
                            score={item.dimensions.data_structuring.score}
                            max={item.dimensions.data_structuring.max}
                          />
                          <DimMiniBar
                            label="Agent"
                            score={item.dimensions.agent_compatibility.score}
                            max={item.dimensions.agent_compatibility.max}
                          />
                          <DimMiniBar
                            label="Trust"
                            score={item.dimensions.trust_signals.score}
                            max={item.dimensions.trust_signals.max}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Stats bar */}
        {!loading && filtered.length > 0 && (
          <div className="flex items-center justify-between mt-6 text-xs text-muted">
            <span>{filtered.length} services</span>
            <span>Average score: {Math.round(filtered.reduce((sum, s) => sum + s.clarvia_score, 0) / filtered.length)}</span>
          </div>
        )}

        {/* CTA */}
        <div className="text-center mt-16 mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 btn-gradient text-white px-8 py-3.5 rounded-xl font-medium text-sm group"
          >
            Scan your service
            <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border/50 px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 rounded-md bg-accent/10 flex items-center justify-center">
              <div className="w-2 h-2 rounded-sm bg-accent" />
            </div>
            <span>Clarvia — Discovery & Trust standard for the agent economy</span>
          </div>
          <a
            href="https://github.com/clarvia-project"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
          >
            GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
