"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE, stripHtml } from "@/lib/api";
import { CASE_STUDIES, scoreColorClass, improvementPercent } from "@/lib/case-studies";

interface TopScore {
  name: string;
  url: string;
  score: number;
  rating: string;
  scan_id: string;
}

const FALLBACK_SCORES: TopScore[] = [
  { name: "Replicate", url: "replicate.com", score: 80, rating: "Strong", scan_id: "" },
  { name: "Helius", url: "helius.dev", score: 72, rating: "Moderate", scan_id: "" },
  { name: "Hugging Face", url: "huggingface.co", score: 70, rating: "Moderate", scan_id: "" },
  { name: "Resend", url: "resend.com", score: 65, rating: "Moderate", scan_id: "" },
  { name: "Google AI", url: "ai.google.dev", score: 64, rating: "Moderate", scan_id: "" },
];

const SCAN_PHASES = [
  "Discovering endpoints...",
  "Checking MCP registries...",
  "Analyzing API documentation...",
  "Probing error structures...",
  "Testing agent compatibility...",
  "Evaluating trust signals...",
  "Calculating Clarvia Score...",
];

const CATEGORY_DISPLAY: Record<string, string> = {
  developer_tools: "Developer Tools",
  ai_llm: "AI/LLM",
  ai: "AI/LLM",
  payments: "Payments",
  communication: "Communication",
  data: "Data",
  productivity: "Productivity",
  blockchain: "Blockchain",
  mcp: "MCP",
  other: "Other",
};

function formatCategory(cat: string): string {
  return CATEGORY_DISPLAY[cat] ?? cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function ScanningOverlay({ url }: { url: string }) {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setPhase((p) => {
        if (p >= SCAN_PHASES.length - 1) return p;
        return p + 1;
      });
    }, 1800);
    return () => clearInterval(timer);
  }, []);

  const progress = ((phase + 1) / SCAN_PHASES.length) * 100;

  return (
    <div className="fixed inset-0 bg-background/95 backdrop-blur-md z-50 flex items-center justify-center">
      <div className="w-full max-w-md px-6 space-y-6">
        <div className="text-center space-y-2">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center glow-accent">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Scanning"
              width={56}
              height={56}
              className="rounded-full animate-pulse"
            />
          </div>
          <p className="text-sm text-muted font-mono">Scanning</p>
          <p className="text-lg font-medium truncate">{url}</p>
        </div>

        <div className="h-1.5 bg-card-border rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${progress}%`,
              background: "linear-gradient(90deg, #3b82f6, #6366f1)",
            }}
          />
        </div>

        <div className="space-y-1.5">
          {SCAN_PHASES.map((label, i) => (
            <p
              key={i}
              className={`text-xs font-mono transition-all duration-300 ${
                i === phase
                  ? "text-foreground"
                  : i < phase
                    ? "text-score-green/60"
                    : "text-muted/20"
              }`}
            >
              {i < phase ? "[done]" : i === phase ? "[....]" : "[    ]"} {label}
            </p>
          ))}
        </div>

        <div className="flex justify-center">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    </div>
  );
}

/* ── Step icons for "How it works" ── */
function IconUrl() {
  return (
    <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 010 5.656l-2.828 2.828a4 4 0 01-5.657-5.656l1.415-1.415M10.172 13.828a4 4 0 010-5.656l2.828-2.828a4 4 0 015.657 5.656l-1.415 1.415" />
    </svg>
  );
}
function IconScore() {
  return (
    <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  );
}
function IconRocket() {
  return (
    <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.84 2.58m0 0a6 6 0 01-7.38-5.84h4.8" />
    </svg>
  );
}

/* ── Dimension icons ── */
function IconApi() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
    </svg>
  );
}
function IconData() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  );
}
function IconAgent() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 14.5M14.25 3.104c.251.023.501.05.75.082M19.8 14.5l-2.234 2.234a2.25 2.25 0 01-1.591.659H8.025a2.25 2.25 0 01-1.591-.659L4.2 14.5m15.6 0l.4.4a2.25 2.25 0 010 3.182l-.9.9a2.25 2.25 0 01-3.182 0l-.4-.4m-7.518 0l-.4.4a2.25 2.25 0 000 3.182l.9.9a2.25 2.25 0 003.182 0l.4-.4" />
    </svg>
  );
}
function IconTrust() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

const DIMENSION_COLORS = [
  { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/20" },
  { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/20" },
  { bg: "bg-cyan-500/10", text: "text-cyan-400", border: "border-cyan-500/20" },
  { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
];

/** Animated counter: counts from 0 to `end` over `duration` ms using ease-out */
function useAnimatedCounter(end: number, duration = 1500) {
  const [value, setValue] = useState(0);
  const prevEnd = useRef(0);

  useEffect(() => {
    if (end === prevEnd.current) return;
    prevEnd.current = end;
    if (end === 0) { setValue(0); return; }

    const start = performance.now();
    let raf: number;

    function tick(now: number) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setValue(Math.round(eased * end));
      if (t < 1) raf = requestAnimationFrame(tick);
    }

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [end, duration]);

  return value;
}

export default function LandingPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [scanningUrl, setScanningUrl] = useState("");
  const [error, setError] = useState("");
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistStatus, setWaitlistStatus] = useState<
    "idle" | "sending" | "done" | "error"
  >("idle");
  const [topScores, setTopScores] = useState<TopScore[]>(FALLBACK_SCORES);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [stats, setStats] = useState({ totalTools: 27886, totalScored: 27886, avgScore: 45, categories: 20, excellentCount: 91 });
  const [altQuery, setAltQuery] = useState("");
  const [altLoading, setAltLoading] = useState(false);
  const [altResults, setAltResults] = useState<{
    service: string;
    category: string;
    alternatives: { name: string; url: string; score: number; category: string; similarity: number; install_hint: string | null; description: string; scan_id: string }[];
    total_in_category: number;
  } | null>(null);
  const [altError, setAltError] = useState("");
  const [topPicks, setTopPicks] = useState<{ name: string; score: number; category: string; scan_id: string; description: string }[]>([]);
  const [topPicksCat, setTopPicksCat] = useState<string>("all");
  const router = useRouter();

  // Animated counters for hero stats
  const animatedTools = useAnimatedCounter(stats.totalTools);
  const animatedScored = useAnimatedCounter(stats.totalScored);
  const animatedCategories = useAnimatedCounter(stats.categories);

  useEffect(() => {
    fetch("/data/prebuilt-scans.json")
      .then((res) => res.json())
      .then((json: { service_name: string; url: string; clarvia_score: number; rating: string; scan_id: string }[]) => {
        const sorted = [...json]
          .sort((a, b) => b.clarvia_score - a.clarvia_score)
          .slice(0, 5)
          .map((s) => ({
            name: s.service_name,
            url: s.url.replace(/^https?:\/\//, ""),
            score: s.clarvia_score,
            rating: s.rating,
            scan_id: s.scan_id,
          }));
        setTopScores(sorted);
      })
      .catch(() => {});
  }, []);

  // Fetch live stats for hero counters
  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/v1/stats`).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/data/prebuilt-scans.json").then((r) => (r.ok ? r.json() : [])).catch(() => []),
    ]).then(([apiStats, scans]) => {
      const scoredCount = Array.isArray(scans) ? scans.length : 0;
      const apiTotal = apiStats?.total_services ?? 0;
      const excellent = Array.isArray(scans) ? scans.filter((s: { clarvia_score: number }) => s.clarvia_score >= 80).length : 0;
      setStats({
        totalTools: apiTotal,
        totalScored: scoredCount || apiTotal,
        avgScore: apiStats?.avg_score || 0,
        categories: apiStats?.categories_count || 20,
        excellentCount: excellent,
      });
    });
  }, []);

  // Fetch top picks (score >= 80)
  useEffect(() => {
    fetch(`${API_BASE}/v1/featured/top?limit=50`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.top_picks) setTopPicks(data.top_picks);
      })
      .catch(() => {});
  }, []);

  const topPicksCategories = ["all", ...new Set(topPicks.map((t) => t.category))];
  const filteredPicks = topPicksCat === "all" ? topPicks : topPicks.filter((t) => t.category === topPicksCat);

  async function handleScan(targetUrl?: string) {
    const scanUrl = targetUrl || url.trim();
    if (!scanUrl) return;

    setLoading(true);
    setScanningUrl(scanUrl);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: scanUrl }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        if (res.status === 429) {
          throw new Error("스캔 한도 초과 (시간당 10회). 잠시 후 다시 시도하세요.");
        }
        throw new Error(data?.detail || "스캔에 실패했습니다. 잠시 후 다시 시도하세요.");
      }

      const data = await res.json();
      router.push(`/scan/${data.scan_id}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setError(msg || "스캔에 실패했습니다. 잠시 후 다시 시도하세요.");
      setLoading(false);
      setScanningUrl("");
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    handleScan();
  }

  async function handleWaitlist(e: React.FormEvent) {
    e.preventDefault();
    if (!waitlistEmail.trim()) return;

    setWaitlistStatus("sending");
    try {
      const res = await fetch(`${API_BASE}/api/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: waitlistEmail.trim() }),
      });
      if (res.ok) {
        setWaitlistStatus("done");
        setWaitlistEmail("");
      } else {
        setWaitlistStatus("error");
      }
    } catch {
      setWaitlistStatus("error");
    }
  }

  async function handleAltSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = altQuery.trim();
    if (!q) return;

    setAltLoading(true);
    setAltError("");
    setAltResults(null);

    try {
      const res = await fetch(
        `${API_BASE}/v1/alternatives/${encodeURIComponent(q)}?limit=6`
      );
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Search failed (${res.status})`);
      }
      const data = await res.json();
      setAltResults(data);
    } catch (err) {
      setAltError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setAltLoading(false);
    }
  }

  return (
    <div className="flex flex-col min-h-screen">
      {loading && <ScanningOverlay url={scanningUrl} />}

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
                href="/docs"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Docs
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden sm:inline text-xs text-muted/60 font-mono">v1.0</span>
            <Link
              href="/register"
              className="text-xs btn-gradient text-white px-4 py-2 rounded-lg font-medium sm:hidden"
            >
              Register
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* ─── Hero ─── */}
        <section className="relative bg-gradient-hero px-6 pt-12 pb-24 overflow-hidden">
          {/* Decorative grid */}
          <div className="absolute inset-0 opacity-[0.03]" style={{
            backgroundImage: "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }} />

          <div className="relative max-w-3xl w-full mx-auto text-center space-y-8">
            {/* Owl mascot */}
            <div className="flex justify-center animate-fade-in mb-[42px]">
              <div className="relative animate-float drop-shadow-[0_0_40px_rgba(37,131,246,0.3)]">
                <Image
                  src="/logos/clarvia-hero.png"
                  alt="Clarvia Owl"
                  width={200}
                  height={200}
                  priority
                  unoptimized
                />
              </div>
            </div>

            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent/20 bg-accent/5 text-xs text-accent font-medium animate-fade-in">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              The AEO standard for AI agents
            </div>

            {/* Stats counters */}
            <div className="flex items-center justify-center gap-8 text-sm font-mono opacity-0 animate-fade-in stagger-2">
              <div className="text-center">
                <div className="text-2xl font-bold text-foreground">{animatedTools.toLocaleString()}+</div>
                <div className="text-xs text-muted">tools indexed</div>
              </div>
              <div className="w-px h-8 bg-card-border" />
              <div className="text-center">
                <div className="text-2xl font-bold text-foreground">{animatedCategories}</div>
                <div className="text-xs text-muted">categories</div>
              </div>
              <div className="w-px h-8 bg-card-border" />
              <div className="text-center">
                <div className="text-2xl font-bold text-foreground">4</div>
                <div className="text-xs text-muted">dimensions</div>
              </div>
            </div>

            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1] animate-fade-in-up">
              Is your service{" "}
              <span className="text-gradient">ready for AI agents?</span>
            </h1>

            <p className="text-lg md:text-xl text-muted max-w-xl mx-auto leading-relaxed opacity-0 animate-fade-in-up stagger-2">
              SEO made you visible to search engines.
              <br className="hidden sm:block" />
              <span className="text-foreground/80">We make you visible to AI agents.</span>
            </p>

            {stats.excellentCount > 0 && (
              <p className="text-sm text-muted/80 font-mono opacity-0 animate-fade-in-up stagger-2">
                {stats.totalScored.toLocaleString()} tools scanned. Only{" "}
                <span className="text-score-green font-semibold">{stats.excellentCount}</span>{" "}
                scored Excellent. Find out where yours stands.
              </p>
            )}

            {/* URL Input */}
            <form onSubmit={handleSubmit} className="flex gap-3 max-w-lg mx-auto pt-4 opacity-0 animate-fade-in-up stagger-3">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Enter any URL (e.g. stripe.com, your-api.com)"
                  className="w-full bg-card-bg/80 border border-card-border rounded-xl px-5 py-3.5 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all font-mono text-sm"
                  disabled={loading}
                />
              </div>
              <button
                type="submit"
                disabled={loading || !url.trim()}
                className="btn-gradient text-white px-7 py-3.5 rounded-xl font-medium text-sm whitespace-nowrap"
              >
                Scan
              </button>
            </form>

            {error && (
              <p className="text-score-red text-sm font-mono">{error}</p>
            )}

            <p className="text-xs text-muted/60 opacity-0 animate-fade-in stagger-4">
              Get your Clarvia Score — the AEO standard for agent discoverability and trust.
            </p>

            {/* Tool directory teaser + alternatives */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 opacity-0 animate-fade-in stagger-4">
              <Link
                href="/tools"
                className="inline-flex items-center gap-3 glass-subtle px-5 py-3 rounded-xl hover:border-accent/30 transition-all group"
              >
                <span className="text-sm text-muted group-hover:text-foreground transition-colors">
                  Explore{" "}
                  <span className="text-foreground font-semibold font-mono">{stats.totalTools.toLocaleString()}+</span>{" "}
                  agent tools
                </span>
                <svg className="w-4 h-4 text-muted group-hover:text-accent group-hover:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
              <span className="text-muted/40 text-xs hidden sm:inline">or</span>
              <form onSubmit={handleAltSearch} className="inline-flex items-center gap-2 glass-subtle px-3 py-1.5 rounded-xl hover:border-accent/30 transition-all">
                <svg className="w-4 h-4 text-muted shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                </svg>
                <input
                  type="text"
                  value={altQuery}
                  onChange={(e) => setAltQuery(e.target.value)}
                  placeholder="Find alternatives to..."
                  className="bg-transparent border-none outline-none text-sm text-foreground placeholder:text-muted/60 w-48 font-mono"
                />
                <button
                  type="submit"
                  disabled={altLoading || !altQuery.trim()}
                  className="text-xs text-accent hover:text-accent/80 font-medium disabled:opacity-40 transition-colors"
                >
                  {altLoading ? "..." : "Go"}
                </button>
              </form>
            </div>

            {/* Alternatives results */}
            {altError && (
              <p className="text-score-red text-sm font-mono">{altError}</p>
            )}
            {altResults && (
              <div className="w-full max-w-2xl mx-auto mt-2 space-y-3 animate-fade-in">
                <div className="flex items-center justify-between px-1">
                  <p className="text-sm text-muted">
                    Alternatives to{" "}
                    <span className="text-foreground font-semibold">{altResults.service}</span>
                    <span className="text-muted/60 ml-2 text-xs font-mono">· {altResults.total_in_category} {formatCategory(altResults.category)} tools</span>
                  </p>
                  <button onClick={() => setAltResults(null)} className="text-xs text-muted hover:text-foreground transition-colors">
                    Clear
                  </button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {altResults.alternatives.map((alt) => (
                    <Link
                      key={alt.scan_id}
                      href={`/scan/${alt.scan_id}`}
                      className="glass-subtle p-3 rounded-xl hover:border-accent/30 transition-all group text-left"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-foreground group-hover:text-accent transition-colors truncate">
                            {alt.name}
                          </p>
                          <p className="text-xs text-muted/60 truncate font-mono">{alt.url}</p>
                        </div>
                        <span className={`text-sm font-bold font-mono shrink-0 ${scoreColor(alt.score)}`}>
                          {alt.score}
                        </span>
                      </div>
                      {alt.description && (
                        <p className="text-xs text-muted mt-1.5 line-clamp-2">{stripHtml(alt.description)}</p>
                      )}
                      {alt.install_hint && (
                        <p className="text-xs font-mono text-accent/70 mt-1 truncate">{alt.install_hint}</p>
                      )}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ─── Use Cases ─── */}
        <section className="relative px-6 py-16 bg-gradient-section">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-10">
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">Use Cases</p>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight">What do you want to do?</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Developer */}
              <a
                href="#scan"
                onClick={(e) => {
                  e.preventDefault();
                  const el = document.querySelector<HTMLInputElement>("input[type='text']");
                  if (el) { el.focus(); el.scrollIntoView({ behavior: "smooth", block: "center" }); }
                }}
                className="glass-card rounded-2xl p-6 flex flex-col gap-4 hover:border-accent/40 transition-all group cursor-pointer"
              >
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 text-lg">
                  {"</>"}
                </div>
                <div>
                  <p className="text-xs font-mono text-accent uppercase tracking-widest mb-1">Developer</p>
                  <h3 className="text-base font-semibold mb-2">Check my API&apos;s AEO score</h3>
                  <p className="text-xs text-muted leading-relaxed">See how agent-ready your service is and get actionable fixes in seconds.</p>
                </div>
                <span className="text-xs text-accent font-medium group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
                  Start scanning &rarr;
                </span>
              </a>

              {/* DevOps */}
              <Link
                href="/docs#badge"
                className="glass-card rounded-2xl p-6 flex flex-col gap-4 hover:border-accent/40 transition-all group"
              >
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400 text-lg">
                  {"[ ]"}
                </div>
                <div>
                  <p className="text-xs font-mono text-accent uppercase tracking-widest mb-1">DevOps</p>
                  <h3 className="text-base font-semibold mb-2">Add an AEO badge to README</h3>
                  <p className="text-xs text-muted leading-relaxed">Show your agent-readiness score on every commit. CI/CD gate included.</p>
                </div>
                <span className="text-xs text-accent font-medium group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
                  Get badge &rarr;
                </span>
              </Link>

              {/* AI Builder */}
              <Link
                href="/leaderboard?type=mcp"
                className="glass-card rounded-2xl p-6 flex flex-col gap-4 hover:border-accent/40 transition-all group"
              >
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 text-lg">
                  {"AI"}
                </div>
                <div>
                  <p className="text-xs font-mono text-accent uppercase tracking-widest mb-1">AI Builder</p>
                  <h3 className="text-base font-semibold mb-2">Connect MCP tools to agents</h3>
                  <p className="text-xs text-muted leading-relaxed">Browse top-ranked MCP services ready to plug into LangChain, CrewAI, and more.</p>
                </div>
                <span className="text-xs text-accent font-medium group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
                  Explore leaderboard &rarr;
                </span>
              </Link>
            </div>
          </div>
        </section>

        {/* ─── Why AEO Matters ─── */}
        <section className="relative px-6 py-24 bg-gradient-section">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">Why it matters</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">AEO is the new SEO</h2>
              <p className="text-sm text-muted max-w-lg mx-auto">
                AI agents are the next wave of API consumers. Services optimized for agents see measurably better outcomes.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  stat: "3.2x",
                  label: "more agent API calls",
                  desc: <>Services with MCP support receive 3.2x more agent API calls. Based on Clarvia AEO Index analysis of 44 services, Mar 2026. <Link href="/methodology" className="text-accent hover:underline">See methodology</Link></>,
                  icon: (
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
                    </svg>
                  ),
                  color: { bg: "bg-blue-500/10", text: "text-blue-400" },
                },
                {
                  stat: "67%",
                  label: "fewer retry failures",
                  desc: <>APIs with structured JSON errors reduce agent retry failures by 67%. Source: error pattern analysis across Clarvia-scanned endpoints. <Link href="/methodology" className="text-accent hover:underline">See methodology</Link></>,
                  icon: (
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  ),
                  color: { bg: "bg-emerald-500/10", text: "text-emerald-400" },
                },
                {
                  stat: "4x",
                  label: "faster discovery",
                  desc: <>OpenAPI-documented services are discovered 4x faster by AI agents. Source: Clarvia discovery latency benchmarks, 44-service dataset. <Link href="/methodology" className="text-accent hover:underline">See methodology</Link></>,
                  icon: (
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                    </svg>
                  ),
                  color: { bg: "bg-purple-500/10", text: "text-purple-400" },
                },
              ].map((item) => (
                <div
                  key={item.stat}
                  className="glass-card rounded-2xl p-8 text-center space-y-4 group transition-all duration-300 hover:-translate-y-1"
                >
                  <div className="flex justify-center">
                    <div className={`w-12 h-12 rounded-xl ${item.color.bg} ${item.color.text} flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
                      {item.icon}
                    </div>
                  </div>
                  <div className={`text-4xl font-bold ${item.color.text}`}>{item.stat}</div>
                  <p className="text-sm font-semibold text-foreground">{item.label}</p>
                  <p className="text-xs text-muted leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── How It Works ─── */}
        <section className="relative px-6 py-24">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">Process</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight">How it works</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  icon: <IconUrl />,
                  step: "01",
                  title: "Enter your URL",
                  desc: "Paste any website or API endpoint to start the analysis.",
                },
                {
                  icon: <IconScore />,
                  step: "02",
                  title: "Get your AEO Score",
                  desc: "We probe your service across 4 dimensions agents care about.",
                },
                {
                  icon: <IconRocket />,
                  step: "03",
                  title: "Improve & get discovered",
                  desc: "Follow actionable recommendations and climb the leaderboard.",
                },
              ].map((item, idx) => (
                <div
                  key={item.step}
                  className="group relative glass-card rounded-2xl p-8 text-center space-y-4 transition-all duration-300 hover:-translate-y-1"
                >
                  {/* Step number */}
                  <div className="absolute top-4 right-5 text-xs font-mono text-muted/30">{item.step}</div>

                  {/* Connector line */}
                  {idx < 2 && (
                    <div className="hidden md:block absolute top-1/2 -right-4 w-8 h-px bg-card-border z-10" />
                  )}

                  <div className="flex justify-center">
                    <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center text-accent group-hover:bg-accent/20 group-hover:scale-110 transition-all duration-300">
                      {item.icon}
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold">{item.title}</h3>
                  <p className="text-sm text-muted leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── What is Clarvia ─── */}
        <section className="relative px-6 py-20 bg-gradient-section">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-3xl mx-auto">
            <div className="glass-card rounded-2xl p-10 space-y-4">
              <p className="text-xs font-mono text-accent uppercase tracking-widest">About</p>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight">What is Clarvia?</h2>
              <p className="text-sm md:text-base text-muted leading-relaxed">
                Clarvia is the AEO (AI Engine Optimization) standard for the agent economy.
                It scans any API, MCP server, CLI tool, or skill and scores it on a 0-100 scale
                for AI agent readiness. With 27,000+ tools indexed across the ecosystem,
                Clarvia helps developers find the best tools for their AI agents,
                and helps API providers optimize their services to be discovered by AI systems.
                The Clarvia Score evaluates four dimensions: API Accessibility, Data Structuring,
                Agent Compatibility, and Trust Signals. Free features include scanning,
                intent-based tool recommendations, side-by-side comparisons, weekly trending,
                and embeddable AEO badges for READMEs.
              </p>
            </div>
          </div>
        </section>

        {/* ─── What We Measure ─── */}
        <section className="relative px-6 py-24 bg-gradient-section">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">Dimensions</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">What we measure</h2>
              <p className="text-sm text-muted max-w-lg mx-auto">
                Every service is evaluated across four dimensions that determine how well AI agents can discover, understand, and trust it.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {[
                {
                  icon: <IconApi />,
                  title: "API Accessibility",
                  desc: "Can agents reach your service?",
                  detail: "Endpoint availability, response speed, authentication documentation.",
                },
                {
                  icon: <IconData />,
                  title: "Data Structuring",
                  desc: "Can agents understand your responses?",
                  detail: "OpenAPI specs, JSON-LD, schema.org markup, structured error responses.",
                },
                {
                  icon: <IconAgent />,
                  title: "Agent Compatibility",
                  desc: "Are you listed where agents look?",
                  detail: "MCP registry presence, plugin manifests, tool descriptions.",
                },
                {
                  icon: <IconTrust />,
                  title: "Trust Signals",
                  desc: "Can agents trust your reliability?",
                  detail: "Uptime signals, HTTPS, security headers, rate limit documentation.",
                },
              ].map((dim, idx) => {
                const color = DIMENSION_COLORS[idx];
                return (
                  <div
                    key={dim.title}
                    className={`glass-card rounded-2xl p-7 space-y-4 group transition-all duration-300 hover:-translate-y-1`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-xl ${color.bg} ${color.text} flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
                        {dim.icon}
                      </div>
                      <div>
                        <h3 className="font-semibold">{dim.title}</h3>
                        <p className={`text-xs ${color.text} font-medium`}>{dim.desc}</p>
                      </div>
                    </div>
                    <p className="text-sm text-muted leading-relaxed pl-14">{dim.detail}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ─── Top Picks ─── */}
        {topPicks.length > 0 && (
          <section className="relative px-6 py-24">
            <div className="divider-gradient absolute top-0 left-0 right-0" />
            <div className="max-w-4xl mx-auto">
              <div className="text-center mb-12">
                <p className="text-xs font-mono text-score-green uppercase tracking-widest mb-3">Agent-Verified</p>
                <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">Top Picks</h2>
                <p className="text-sm text-muted">
                  {stats.totalScored.toLocaleString()}+ tools scanned. Only <span className="text-score-green font-semibold">{topPicks.length}</span> scored 80+.
                  These are the most agent-ready services in the ecosystem.
                </p>
              </div>

              {/* Category tabs */}
              <div className="flex flex-wrap gap-2 justify-center mb-8">
                {topPicksCategories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setTopPicksCat(cat)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                      topPicksCat === cat
                        ? "bg-accent/20 text-accent border border-accent/30"
                        : "bg-card-bg/50 text-muted border border-card-border/30 hover:text-foreground"
                    }`}
                  >
                    {cat === "all" ? "All" : cat.replace(/_/g, " ")}
                  </button>
                ))}
              </div>

              {/* Cards grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredPicks.slice(0, 12).map((tool) => (
                  <Link
                    key={tool.scan_id}
                    href={`/report/${tool.scan_id}`}
                    className="glass-card rounded-xl p-5 hover:border-accent/30 transition-all group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm truncate group-hover:text-accent transition-colors">{tool.name}</h3>
                        <p className="text-xs text-muted font-mono">{tool.category.replace(/_/g, " ")}</p>
                      </div>
                      <div className="flex items-center gap-1.5 ml-3">
                        <span className={`text-lg font-bold ${scoreColor(tool.score)}`}>{tool.score}</span>
                      </div>
                    </div>
                    {tool.description && (
                      <p className="text-xs text-muted/70 line-clamp-2">{tool.description}</p>
                    )}
                  </Link>
                ))}
              </div>

              {filteredPicks.length > 12 && (
                <div className="text-center mt-8">
                  <Link
                    href="/leaderboard"
                    className="text-sm text-accent hover:text-accent/80 font-mono"
                  >
                    View all {filteredPicks.length} top picks →
                  </Link>
                </div>
              )}
            </div>
          </section>
        )}

        {/* ─── Leaderboard Preview ─── */}
        <section className="relative px-6 py-24">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-12">
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">Rankings</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">Leaderboard</h2>
              <p className="text-sm text-muted">
                Services ranked by agent-readiness. Where does yours stand?
              </p>
            </div>
            <div className="glass-card rounded-2xl overflow-hidden">
              <div className="grid grid-cols-[auto_1fr_auto_auto] gap-4 px-6 py-3.5 border-b border-card-border/50 text-xs text-muted font-mono uppercase tracking-wider">
                <span>#</span>
                <span>Service</span>
                <span>Score</span>
                <span>Rating</span>
              </div>
              {topScores.map((item, i) => (
                <button
                  key={item.name}
                  onClick={() =>
                    item.scan_id
                      ? router.push(`/scan/${item.scan_id}`)
                      : handleScan(item.url)
                  }
                  disabled={loading}
                  className={`w-full grid grid-cols-[auto_1fr_auto_auto] gap-4 px-6 py-4 text-left transition-all duration-200 disabled:opacity-50 border-b border-card-border/30 last:border-b-0 group ${
                    i === 0 ? "rank-gold-row hover:bg-yellow-500/5" :
                    i === 1 ? "rank-silver-row hover:bg-gray-400/5" :
                    i === 2 ? "rank-bronze-row hover:bg-orange-500/5" :
                    "hover:bg-card-border/20"
                  }`}
                >
                  <span className="text-sm font-mono w-6">
                    {i === 0 ? (
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full badge-gold text-[10px] font-bold">1</span>
                    ) : i === 1 ? (
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full badge-silver text-[10px] font-bold">2</span>
                    ) : i === 2 ? (
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full badge-bronze text-[10px] font-bold">3</span>
                    ) : (
                      <span className="text-muted">{i + 1}</span>
                    )}
                  </span>
                  <span className="text-sm font-medium truncate group-hover:text-accent transition-colors">{item.name}</span>
                  <span className={`text-sm font-mono font-bold ${scoreColor(item.score)}`}>
                    {item.score}
                  </span>
                  <span className="text-xs text-muted">{item.rating}</span>
                </button>
              ))}
            </div>
            <div className="text-center mt-8">
              <Link
                href="/leaderboard"
                className="inline-flex items-center gap-2 text-sm text-accent hover:text-accent-hover transition-colors font-medium group"
              >
                View full leaderboard
                <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </section>

        {/* ─── For Developers CTA ─── */}
        <section className="relative px-6 py-24 bg-gradient-section">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-4xl mx-auto text-center space-y-10">
            <div>
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">For developers</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Ship agent-ready services</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm max-w-4xl mx-auto">
              {[
                { label: "Register your MCP server or API", step: "1" },
                { label: "Get scored automatically", step: "2" },
                { label: "Add badge to README", step: "3" },
                { label: "Get discovered by agents", step: "4" },
              ].map((item, idx) => (
                <div key={idx} className="glass-card rounded-xl px-4 py-3 text-muted flex items-center gap-2 text-center">
                  <span className="w-5 h-5 rounded-md bg-accent/10 text-accent text-[10px] font-bold flex items-center justify-center flex-shrink-0">{item.step}</span>
                  <span className="text-xs">{item.label}</span>
                </div>
              ))}
            </div>
            <div className="pt-2">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 btn-gradient text-white px-8 py-3.5 rounded-xl font-medium text-sm group"
              >
                Register now
                <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </section>

        {/* ─── Waitlist ─── */}
        <section className="relative px-6 py-24">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-lg mx-auto text-center space-y-6">
            <div>
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">Coming soon</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Stay in the loop</h2>
            </div>
            <p className="text-sm text-muted">
              Get notified when we launch enterprise features: continuous
              monitoring, CI/CD integration, and team dashboards.
            </p>
            {waitlistStatus === "done" ? (
              <div className="glass-card rounded-xl p-6">
                <p className="text-score-green text-sm font-mono">
                  You&apos;re on the list! We&apos;ll be in touch.
                </p>
              </div>
            ) : (
              <form
                onSubmit={handleWaitlist}
                className="flex gap-3 max-w-sm mx-auto pt-2"
              >
                <input
                  type="email"
                  value={waitlistEmail}
                  onChange={(e) => setWaitlistEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="flex-1 bg-card-bg/80 border border-card-border rounded-xl px-5 py-3 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all text-sm"
                  required
                />
                <button
                  type="submit"
                  disabled={waitlistStatus === "sending"}
                  className="glass-card hover:border-accent/50 text-foreground px-5 py-3 rounded-xl text-sm font-medium transition-all whitespace-nowrap disabled:opacity-50"
                >
                  {waitlistStatus === "sending" ? "..." : "Notify me"}
                </button>
              </form>
            )}
            {waitlistStatus === "error" && (
              <p className="text-score-red text-xs font-mono">
                Something went wrong. Try again.
              </p>
            )}
          </div>
        </section>

        {/* ─── Success Stories (Causation Proof) ─── */}
        <section className="relative px-6 py-24 bg-gradient-section">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">Proven results</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
                Higher scores. More agent traffic.
              </h2>
              <p className="text-sm text-muted max-w-lg mx-auto">
                Improving your AEO score directly increases how often AI agents discover and use your service.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {CASE_STUDIES.map((cs) => (
                <div
                  key={cs.slug}
                  className="glass-card rounded-2xl p-8 space-y-5 group transition-all duration-300 hover:-translate-y-1"
                >
                  {/* Header: name + category */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold">{cs.tool_name}</h3>
                      <p className="text-xs text-muted/60 font-mono">{cs.category}</p>
                    </div>
                    <span className="text-xs font-mono px-2 py-1 rounded-md bg-accent/10 text-accent">
                      {cs.timeframe}
                    </span>
                  </div>

                  {/* Score bar: before → after */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className={scoreColorClass(cs.before_score)}>
                        {cs.before_score}
                      </span>
                      <span className="text-muted/40 mx-2">→</span>
                      <span className={`font-bold ${scoreColorClass(cs.after_score)}`}>
                        {cs.after_score}
                      </span>
                      <span className="ml-auto text-score-green text-xs">
                        +{improvementPercent(cs.before_score, cs.after_score)}%
                      </span>
                    </div>
                    <div className="h-2 bg-card-border/30 rounded-full overflow-hidden relative">
                      <div
                        className="absolute inset-y-0 left-0 rounded-full bg-muted/20"
                        style={{ width: `${cs.before_score}%` }}
                      />
                      <div
                        className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
                        style={{
                          width: `${cs.after_score}%`,
                          background: cs.after_score >= 70
                            ? "linear-gradient(90deg, #22c55e, #4ade80)"
                            : "linear-gradient(90deg, #eab308, #facc15)",
                        }}
                      />
                    </div>
                  </div>

                  {/* Metric highlight */}
                  <div className="flex items-center gap-3 py-3 px-4 rounded-xl bg-score-green/5 border border-score-green/10">
                    <span className="text-2xl font-bold text-score-green font-mono">
                      {cs.metric_multiplier}x
                    </span>
                    <span className="text-sm text-muted">
                      {cs.metric_improvement.replace(/^\d+x\s*/, "")}
                    </span>
                  </div>

                  <div className="h-px bg-card-border/50" />

                  {/* Changes list */}
                  <div className="space-y-1.5">
                    {cs.changes_made.slice(0, 3).map((change, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-muted">
                        <span className="text-score-green mt-0.5 shrink-0">+</span>
                        <span>{change}</span>
                      </div>
                    ))}
                    {cs.changes_made.length > 3 && (
                      <p className="text-xs text-muted/40 pl-4">
                        +{cs.changes_made.length - 3} more changes
                      </p>
                    )}
                  </div>

                  {/* Quote */}
                  <p className="text-xs text-muted/70 leading-relaxed italic border-l-2 border-accent/20 pl-3">
                    &ldquo;{cs.quote}&rdquo;
                  </p>

                  {/* Dimension tags */}
                  <div className="flex flex-wrap gap-1.5">
                    {cs.dimensions_improved.map((dim) => (
                      <span
                        key={dim}
                        className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-accent/5 text-accent/70 border border-accent/10"
                      >
                        {dim}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* CTA below case studies */}
            <div className="text-center mt-12">
              <p className="text-sm text-muted mb-4">
                Want results like these? Start with a free scan.
              </p>
              <button
                onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                className="btn-gradient text-white px-6 py-3 rounded-xl font-medium text-sm inline-flex items-center gap-2"
              >
                Scan your service
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
                </svg>
              </button>
            </div>
          </div>
        </section>

        {/* ─── FAQ ─── */}
        <section className="relative px-6 py-24">
          <div className="divider-gradient absolute top-0 left-0 right-0" />
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">FAQ</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Frequently asked questions</h2>
            </div>
            <div className="space-y-3">
              {[
                {
                  q: "What is AEO?",
                  a: "AEO (AI Engine Optimization) is the practice of making your API or service easily discoverable and usable by AI agents. Think of it as SEO, but for AI instead of search engines.",
                },
                {
                  q: "How is the Clarvia Score calculated?",
                  a: "methodology",
                },
                {
                  q: "Is it free?",
                  a: "Yes! Basic scanning is completely free with no signup required. Premium features like continuous monitoring, CI/CD integration, and team dashboards are available on paid plans.",
                },
                {
                  q: "What happens if my score is low?",
                  a: "A low score means AI agents may have difficulty discovering or using your service. Each scan result includes specific, actionable recommendations to improve your score.",
                },
                {
                  q: "Does a higher score guarantee more agent traffic?",
                  a: "A higher AEO score means your service is better optimized for agent discovery and usage. While we can't guarantee specific traffic numbers, our data shows that well-optimized services receive significantly more agent API calls.",
                },
              ].map((item, idx) => (
                <div
                  key={idx}
                  className="glass-card rounded-2xl overflow-hidden transition-all duration-300"
                >
                  <button
                    onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                    className="w-full flex items-center justify-between px-7 py-5 text-left group"
                  >
                    <span className="text-sm font-semibold text-foreground group-hover:text-accent transition-colors">
                      {item.q}
                    </span>
                    <svg
                      className={`w-5 h-5 text-muted flex-shrink-0 transition-transform duration-300 ${openFaq === idx ? "rotate-180" : ""}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={1.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                    </svg>
                  </button>
                  {openFaq === idx && (
                    <div className="px-7 pb-6">
                      <p className="text-sm text-muted leading-relaxed">
                        {item.a === "methodology" ? (
                          <>
                            We evaluate your service across four dimensions: API Accessibility, Data Structuring, Agent Compatibility, and Trust Signals. Each dimension is scored independently and weighted to produce your overall Clarvia Score.{" "}
                            <Link href="/methodology" className="text-accent hover:underline font-medium">
                              See full methodology &rarr;
                            </Link>
                          </>
                        ) : (
                          item.a
                        )}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── Disclaimer ─── */}
        <section className="px-6 py-12">
          <div className="divider-gradient mb-12" />
          <div className="max-w-3xl mx-auto text-center">
            <p className="text-xs text-muted/50 leading-relaxed">
              Clarvia Score does not measure a company&apos;s size or quality.
              It measures how easily AI agents can discover and use this service.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border/50 px-6 py-10">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Clarvia"
              width={24}
              height={24}
              className="rounded-full"
            />
            <span className="text-xs text-muted">Built for the agent economy</span>
          </div>
          <div className="flex items-center gap-4 flex-wrap justify-center text-xs text-muted">
            <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy</Link>
            <a href="https://github.com/clarvia-project" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">GitHub</a>
            <a href="https://x.com/clarvia_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">@clarvia_ai</a>
            <Link href="/about" className="hover:text-foreground transition-colors">About</Link>
            <span className="text-muted/50 cursor-default" title="Coming soon">Terms</span>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
