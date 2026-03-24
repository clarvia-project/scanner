"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";

// ----- Types -----

interface Dimension {
  score: number;
  max: number;
  sub_factors?: Record<string, { score: number; max: number; label: string }>;
}

interface ScanEntry {
  scan_id: string;
  url: string;
  service_name: string;
  clarvia_score: number;
  rating: string;
  dimensions: {
    api_accessibility: Dimension;
    data_structuring: Dimension;
    agent_compatibility: Dimension;
    trust_signals: Dimension;
  };
}

// ----- Categories for agent builders -----

const AGENT_CATEGORIES: Record<string, string[]> = {
  "AI / LLM Providers": [
    "openai", "anthropic", "google ai", "mistral", "cohere",
    "replicate", "hugging face", "together ai", "groq", "perplexity",
  ],
  "Blockchain Data": [
    "alchemy", "infura", "quicknode", "the graph", "goldsky",
    "helius", "dune", "flipside", "moralis", "solana", "ethereum",
  ],
  "Developer Infra": [
    "github", "gitlab", "vercel", "netlify", "supabase",
    "firebase", "cloudflare", "railway", "render",
  ],
  "Communication": ["slack", "discord", "twilio", "sendgrid", "resend"],
  "Productivity": ["notion", "linear", "atlassian", "asana", "figma", "canva"],
  "Payments": ["stripe", "paypal", "squareup", "plaid", "coinbase", "circle"],
};

function matchCategory(name: string): string {
  const lower = name.toLowerCase();
  for (const [cat, keywords] of Object.entries(AGENT_CATEGORIES)) {
    if (keywords.some((k) => lower.includes(k))) return cat;
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

function MiniDimBar({ label, score, max }: { label: string; score: number; max: number }) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] text-muted w-8 text-right font-mono shrink-0">{label}</span>
      <div className="flex-1 h-1 bg-card-border/40 rounded-full overflow-hidden min-w-[32px]">
        <div className={`h-full rounded-full ${dimBarGradient(score, max)}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-muted font-mono w-6 shrink-0">{score}</span>
    </div>
  );
}

function ServiceCard({ entry, rank }: { entry: ScanEntry; rank: number }) {
  return (
    <Link
      href={`/scan/${entry.scan_id}`}
      className="glass-card rounded-xl p-5 hover:border-accent/30 transition-all duration-200 group block"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-muted/50">#{rank}</span>
            <h3 className="text-sm font-semibold group-hover:text-accent transition-colors truncate">
              {entry.service_name}
            </h3>
          </div>
          <p className="text-xs text-muted font-mono truncate mt-0.5">
            {entry.url.replace(/^https?:\/\//, "")}
          </p>
        </div>
        <div className="text-right shrink-0 ml-3">
          <div className={`text-lg font-mono font-bold ${scoreColor(entry.clarvia_score)}`}>
            {entry.clarvia_score}
          </div>
          <span className={`inline-block px-2 py-0.5 rounded text-[9px] font-mono uppercase ${ratingBadgeClass(entry.rating)}`}>
            {entry.rating}
          </span>
        </div>
      </div>
      <div className="space-y-1">
        <MiniDimBar label="API" score={entry.dimensions.api_accessibility.score} max={entry.dimensions.api_accessibility.max} />
        <MiniDimBar label="Data" score={entry.dimensions.data_structuring.score} max={entry.dimensions.data_structuring.max} />
        <MiniDimBar label="Agent" score={entry.dimensions.agent_compatibility.score} max={entry.dimensions.agent_compatibility.max} />
        <MiniDimBar label="Trust" score={entry.dimensions.trust_signals.score} max={entry.dimensions.trust_signals.max} />
      </div>
    </Link>
  );
}

// ----- Main Page -----

export default function ForAgentsPage() {
  const [data, setData] = useState<ScanEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [compareSet, setCompareSet] = useState<Set<string>>(new Set());
  const router = useRouter();

  useEffect(() => {
    fetch("/data/prebuilt-scans.json")
      .then((res) => res.json())
      .then((json: ScanEntry[]) => {
        json.sort((a, b) => b.clarvia_score - a.clarvia_score);
        setData(json);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(() => {
    const cats = new Set<string>();
    data.forEach((d) => cats.add(matchCategory(d.service_name)));
    return ["All", ...Array.from(cats).sort()];
  }, [data]);

  const filtered = useMemo(() => {
    let list = data;
    if (activeCategory !== "All") {
      list = list.filter((d) => matchCategory(d.service_name) === activeCategory);
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (d) => d.service_name.toLowerCase().includes(q) || d.url.toLowerCase().includes(q),
      );
    }
    return list;
  }, [data, activeCategory, search]);

  const compareItems = useMemo(
    () => data.filter((d) => compareSet.has(d.scan_id)),
    [data, compareSet],
  );

  function toggleCompare(scanId: string) {
    setCompareSet((prev) => {
      const next = new Set(prev);
      if (next.has(scanId)) next.delete(scanId);
      else if (next.size < 3) next.add(scanId);
      return next;
    });
  }

  return (
    <div className="flex flex-col min-h-screen bg-gradient-mesh">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-card-border/50 backdrop-blur-xl bg-background/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
              <Image
                src="/logos/clarvia-icon.svg"
                alt="Clarvia"
                width={32}
                height={32}
                className="rounded-full group-hover:scale-110 transition-transform duration-200"
              />
              <span className="font-semibold text-base tracking-tight text-foreground">
                clarvia
              </span>
            </Link>
            <nav className="hidden sm:flex items-center gap-6">
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">
                Leaderboard
              </Link>
              <Link href="/for-agents" className="text-sm text-foreground font-medium">
                For Agents
              </Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">
                Docs
              </Link>
            </nav>
          </div>
          <span className="text-xs text-muted/60 font-mono hidden sm:inline">v1.0</span>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden">
          <div className="max-w-6xl mx-auto px-6 pt-20 pb-16 text-center">
            <p className="text-xs font-mono text-accent uppercase tracking-widest mb-4">
              For Agent Builders
            </p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
              Find the most{" "}
              <span className="bg-gradient-to-r from-accent to-purple-400 bg-clip-text text-transparent">
                agent-ready
              </span>{" "}
              APIs
            </h1>
            <p className="text-muted text-base md:text-lg max-w-2xl mx-auto mb-10">
              Stop guessing which APIs work with your agents. Use AEO scores to pick services
              that have proper schemas, MCP support, and reliable endpoints.
            </p>

            {/* Search bar */}
            <div className="max-w-lg mx-auto relative">
              <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search APIs by name or URL..."
                className="w-full bg-card-bg/80 border border-card-border rounded-xl pl-12 pr-4 py-4 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all font-mono text-sm"
              />
            </div>
          </div>
        </section>

        {/* Value Props */}
        <section className="max-w-6xl mx-auto px-6 pb-16">
          <div className="grid sm:grid-cols-3 gap-6">
            <div className="glass-card rounded-xl p-6 text-center">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                </svg>
              </div>
              <h3 className="text-sm font-semibold mb-2">Scored &amp; Ranked</h3>
              <p className="text-xs text-muted">
                Every API scored on 4 dimensions: accessibility, data structure, agent compatibility, and trust signals.
              </p>
            </div>

            <div className="glass-card rounded-xl p-6 text-center">
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
                </svg>
              </div>
              <h3 className="text-sm font-semibold mb-2">Side-by-Side Compare</h3>
              <p className="text-xs text-muted">
                Compare up to 3 APIs across all dimensions. Pick the best fit for your agent stack.
              </p>
            </div>

            <div className="glass-card rounded-xl p-6 text-center">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
                </svg>
              </div>
              <h3 className="text-sm font-semibold mb-2">MCP-Ready Detection</h3>
              <p className="text-xs text-muted">
                Instantly see which APIs have MCP server support, OpenAPI specs, and structured error handling.
              </p>
            </div>
          </div>
        </section>

        {/* Category Filters + API Grid */}
        <section className="max-w-6xl mx-auto px-6 pb-20">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold">Top Agent-Ready APIs</h2>
            <span className="text-xs text-muted font-mono">{filtered.length} services</span>
          </div>

          {/* Category pills */}
          <div className="flex flex-wrap gap-2 mb-8">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-4 py-2 rounded-xl text-xs font-medium transition-all duration-200 border ${
                  activeCategory === cat
                    ? "btn-gradient text-white border-transparent shadow-md shadow-accent/10"
                    : "bg-card-bg/60 text-muted border-card-border hover:border-accent/30 hover:text-foreground"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Quick compare bar */}
          {compareSet.size >= 2 && (
            <div className="flex items-center justify-between glass-card rounded-xl px-5 py-3 mb-6">
              <div className="flex items-center gap-3 text-sm">
                <span className="text-muted">Comparing:</span>
                {compareItems.map((item) => (
                  <span key={item.scan_id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-accent/10 text-accent text-xs font-medium">
                    {item.service_name}
                    <button onClick={() => toggleCompare(item.scan_id)} className="hover:text-foreground">
                      &#x2715;
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={`/leaderboard`}
                  className="btn-gradient text-white px-4 py-2 rounded-lg text-xs font-medium"
                >
                  Full Compare
                </Link>
                <button
                  onClick={() => setCompareSet(new Set())}
                  className="text-xs text-muted hover:text-foreground"
                >
                  Clear
                </button>
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-muted text-sm mb-4">No APIs found matching your search.</p>
              <button
                onClick={() => { setActiveCategory("All"); setSearch(""); }}
                className="text-accent text-sm hover:text-accent-hover transition-colors"
              >
                Clear filters
              </button>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.slice(0, 30).map((entry, idx) => (
                <div key={entry.scan_id} className="relative">
                  <ServiceCard entry={entry} rank={idx + 1} />
                  {/* Compare toggle */}
                  <button
                    onClick={(e) => { e.preventDefault(); toggleCompare(entry.scan_id); }}
                    className={`absolute top-3 right-3 w-6 h-6 rounded-md border flex items-center justify-center transition-all text-xs ${
                      compareSet.has(entry.scan_id)
                        ? "border-accent bg-accent/20 text-accent"
                        : "border-card-border/50 text-muted/30 hover:border-accent/30 hover:text-muted"
                    }`}
                    title="Add to compare"
                  >
                    {compareSet.has(entry.scan_id) ? "\u2713" : "+"}
                  </button>
                </div>
              ))}
            </div>
          )}

          {filtered.length > 30 && (
            <div className="text-center mt-8">
              <Link
                href="/leaderboard"
                className="text-sm text-accent hover:text-accent-hover transition-colors"
              >
                View all {filtered.length} services on the leaderboard &rarr;
              </Link>
            </div>
          )}
        </section>

        {/* CTA Section */}
        <section className="border-t border-card-border/50 bg-card-bg/30">
          <div className="max-w-3xl mx-auto px-6 py-20 text-center">
            <h2 className="text-2xl md:text-3xl font-bold mb-4">
              Don&apos;t see the API you need?
            </h2>
            <p className="text-muted text-sm md:text-base mb-8 max-w-lg mx-auto">
              Scan any public API endpoint and get its AEO score in seconds. Free, no signup required.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 btn-gradient text-white px-8 py-3.5 rounded-xl font-medium text-sm group"
            >
              Scan any API
              <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border/50 px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <div className="flex items-center gap-3">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Clarvia"
              width={24}
              height={24}
              className="rounded-full"
            />
            <span>Clarvia — Discovery &amp; Trust standard for the agent economy</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy</Link>
            <a href="https://github.com/clarvia-project" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">GitHub</a>
            <a href="https://x.com/clarvia_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">@clarvia_ai</a>
            <Link href="/about" className="hover:text-foreground transition-colors">About</Link>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
