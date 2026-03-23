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
      return "bg-score-green/15 text-score-green border border-score-green/30";
    case "Moderate":
    case "Good":
      return "bg-score-yellow/15 text-score-yellow border border-score-yellow/30";
    case "Basic":
      return "bg-score-yellow/15 text-score-yellow border border-score-yellow/30";
    default:
      return "bg-score-red/15 text-score-red border border-score-red/30";
  }
}

function dimBarColor(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bg-score-green";
  if (pct >= 0.4) return "bg-score-yellow";
  return "bg-score-red";
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
      <div className="flex-1 h-1.5 bg-card-border rounded-full overflow-hidden min-w-[40px]">
        <div
          className={`h-full rounded-full ${dimBarColor(score, max)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-muted font-mono w-8 shrink-0">
        {score}/{max}
      </span>
    </div>
  );
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
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-card-border px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className="font-mono text-sm tracking-widest text-muted uppercase hover:text-foreground transition-colors"
            >
              Clarvia
            </Link>
            <Link
              href="/leaderboard"
              className="text-xs text-foreground font-medium hover:text-accent transition-colors"
            >
              Leaderboard
            </Link>
            <Link
              href="/register"
              className="text-xs text-muted hover:text-foreground transition-colors"
            >
              Register
            </Link>
          </div>
          <span className="text-xs text-muted">AEO Scanner v1.0</span>
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-10">
        {/* Title */}
        <div className="text-center space-y-3 mb-10">
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
            AEO Leaderboard
          </h1>
          <p className="text-muted text-sm md:text-base max-w-xl mx-auto">
            How agent-ready is your favorite service?
          </p>
        </div>

        {/* Search */}
        <div className="mb-6 max-w-md mx-auto">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search services..."
            className="w-full bg-card-bg border border-card-border rounded-lg px-4 py-2.5 text-foreground placeholder:text-muted/50 focus:outline-none focus:border-accent transition-colors font-mono text-sm"
          />
        </div>

        {/* Category filters */}
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors border ${
                category === cat
                  ? "bg-accent text-white border-accent"
                  : "bg-card-bg text-muted border-card-border hover:border-accent/50"
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
          <p className="text-center text-muted text-sm py-20">
            No services found.
          </p>
        ) : (
          /* Table */
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-card-border text-left text-xs text-muted uppercase tracking-wider">
                  <th className="pb-3 pr-3 w-10">#</th>
                  <th className="pb-3 pr-3">Service</th>
                  <th className="pb-3 pr-3 text-center w-16">Score</th>
                  <th className="pb-3 pr-3 text-center w-24">Rating</th>
                  <th className="pb-3 hidden lg:table-cell min-w-[280px]">
                    Dimensions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, idx) => (
                  <tr
                    key={item.scan_id}
                    onClick={() => router.push(`/scan/${item.scan_id}`)}
                    className="border-b border-card-border/50 hover:bg-card-bg/60 cursor-pointer transition-colors group"
                  >
                    {/* Rank */}
                    <td className="py-3 pr-3 font-mono text-muted text-xs">
                      {idx + 1}
                    </td>

                    {/* Service name + URL */}
                    <td className="py-3 pr-3">
                      <div className="font-medium group-hover:text-accent transition-colors">
                        {item.service_name}
                      </div>
                      <div className="text-xs text-muted font-mono truncate max-w-[200px]">
                        {item.url.replace(/^https?:\/\//, "")}
                      </div>
                    </td>

                    {/* Score */}
                    <td className="py-3 pr-3 text-center">
                      <span
                        className={`font-mono font-bold text-lg ${scoreColor(item.clarvia_score)}`}
                      >
                        {item.clarvia_score}
                      </span>
                    </td>

                    {/* Rating badge */}
                    <td className="py-3 pr-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider ${ratingBadgeClass(item.rating)}`}
                      >
                        {item.rating}
                      </span>
                    </td>

                    {/* Dimension bars */}
                    <td className="py-3 hidden lg:table-cell">
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
        )}

        {/* CTA */}
        <div className="text-center mt-12 mb-6">
          <Link
            href="/"
            className="inline-block bg-accent hover:bg-accent-hover text-white px-8 py-3 rounded-lg font-medium transition-colors text-sm"
          >
            Scan your service
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border px-6 py-6">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted">
          <span>
            Clarvia — Discovery & Trust standard for the agent economy
          </span>
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
