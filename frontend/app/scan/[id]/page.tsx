"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ----- Types -----

interface SubFactor {
  score: number;
  max: number;
  label: string;
  evidence: Record<string, unknown>;
}

interface Dimension {
  score: number;
  max: number;
  sub_factors: Record<string, SubFactor>;
}

interface OnchainBonus {
  score: number;
  max: number;
  applicable: boolean;
  sub_factors: Record<string, SubFactor>;
}

interface ScanResult {
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
  onchain_bonus: OnchainBonus;
  top_recommendations: string[];
  scanned_at: string;
  scan_duration_ms: number;
}

// ----- Helpers -----

function scoreColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#eab308";
  return "#ef4444";
}

function scoreTextClass(score: number): string {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function scoreBgGradient(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bar-gradient-green";
  if (pct >= 0.4) return "bar-gradient-yellow";
  return "bar-gradient-red";
}

function scoreGlowClass(score: number): string {
  if (score >= 70) return "glow-green";
  if (score >= 40) return "glow-yellow";
  return "glow-red";
}

function gradeBadgeClass(rating: string): string {
  switch (rating) {
    case "Exceptional":
    case "Strong":
      return "bg-score-green/10 text-score-green border-score-green/20";
    case "Moderate":
    case "Good":
      return "bg-score-yellow/10 text-score-yellow border-score-yellow/20";
    case "Basic":
      return "bg-score-yellow/10 text-score-yellow border-score-yellow/20";
    default:
      return "bg-score-red/10 text-score-red border-score-red/20";
  }
}

const DIMENSION_META: Record<string, { label: string; description: string; color: string; iconColor: string }> = {
  api_accessibility: {
    label: "API Accessibility",
    description: "How easily agents can reach and authenticate with your API",
    color: "blue",
    iconColor: "text-blue-400",
  },
  data_structuring: {
    label: "Data Structuring",
    description: "Schema definition, pricing clarity, and error handling",
    color: "purple",
    iconColor: "text-purple-400",
  },
  agent_compatibility: {
    label: "Agent Compatibility",
    description: "MCP support, robot policies, and discovery mechanisms",
    color: "cyan",
    iconColor: "text-cyan-400",
  },
  trust_signals: {
    label: "Trust Signals",
    description: "Uptime, documentation quality, and update frequency",
    color: "emerald",
    iconColor: "text-emerald-400",
  },
};

function priorityIcon(index: number): string {
  if (index === 0) return "!!!";
  if (index < 3) return "!!";
  return "!";
}

function priorityColorClass(index: number): string {
  if (index === 0) return "text-score-red";
  if (index < 3) return "text-score-yellow";
  return "text-muted";
}

function priorityBgClass(index: number): string {
  if (index === 0) return "border-score-red/20 bg-score-red/5";
  if (index < 3) return "border-score-yellow/20 bg-score-yellow/5";
  return "border-card-border bg-card-bg";
}

function formatEvidence(evidence: Record<string, unknown>): string[] {
  const lines: string[] = [];
  for (const [key, value] of Object.entries(evidence)) {
    if (key === "reason" && typeof value === "string") {
      lines.unshift(value);
    } else if (key === "url" && typeof value === "string") {
      lines.push(`Source: ${value}`);
    } else if (key === "keywords_found" && Array.isArray(value)) {
      lines.push(`Keywords: ${value.join(", ")}`);
    } else if (key === "signals" && typeof value === "object" && value) {
      const signals = Object.entries(value as Record<string, boolean>)
        .filter(([, v]) => v)
        .map(([k]) => k.replace(/_/g, " "));
      if (signals.length) lines.push(`Signals: ${signals.join(", ")}`);
    } else if (key === "p50_ms" && typeof value === "number") {
      lines.push(`Median response: ${value}ms`);
    } else if (key === "status" && typeof value === "number") {
      lines.push(`HTTP ${value}`);
    } else if (key === "indicators" && Array.isArray(value)) {
      lines.push(`Indicators: ${value.join(", ")}`);
    } else if (key === "method" && typeof value === "string") {
      lines.push(`Method: ${value}`);
    } else if (key === "github_bonus" && typeof value === "number") {
      lines.push(`GitHub activity bonus: +${value}`);
    } else if (key === "graphql_bonus" && typeof value === "number") {
      lines.push(`GraphQL bonus: +${value}`);
    }
  }
  return lines;
}

// ----- Animated Score Counter -----

function useAnimatedNumber(target: number, duration: number = 1200): number {
  const [current, setCurrent] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const start = performance.now();
    const from = 0;

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(from + (target - from) * eased));

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return current;
}

// ----- Score Gauge Component -----

function ScoreGauge({ score }: { score: number }) {
  const animatedScore = useAnimatedNumber(score);
  const color = scoreColor(animatedScore);
  const circumference = 2 * Math.PI * 54;
  const progress = (animatedScore / 100) * circumference;
  const glowClass = scoreGlowClass(animatedScore);

  return (
    <div className={`relative w-44 h-44 mx-auto ${glowClass} rounded-full`}>
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        {/* Background track */}
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke="rgba(30, 42, 58, 0.5)"
          strokeWidth="7"
        />
        {/* Progress arc */}
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          className="transition-[stroke] duration-300"
          style={{
            filter: `drop-shadow(0 0 6px ${color}40)`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="text-5xl font-mono font-bold transition-[color] duration-300"
          style={{ color }}
        >
          {animatedScore}
        </span>
        <span className="text-xs text-muted mt-1 font-mono">/ 100</span>
      </div>
    </div>
  );
}

// ----- Dimension Bar Component -----

function DimensionBar({
  dimKey,
  dimension,
}: {
  dimKey: string;
  dimension: Dimension;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = DIMENSION_META[dimKey];
  const pct = dimension.max > 0 ? (dimension.score / dimension.max) * 100 : 0;

  return (
    <div className="glass-card rounded-xl overflow-hidden transition-all duration-300">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-5 text-left flex items-center gap-4 hover:bg-card-border/10 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${meta?.iconColor || "text-foreground"}`}>{meta?.label || dimKey}</span>
            </div>
            <span className="font-mono text-sm text-muted">
              {dimension.score}/{dimension.max}
            </span>
          </div>
          <div className="h-2.5 bg-card-border/40 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${scoreBgGradient(dimension.score, dimension.max)}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-muted transition-transform duration-200 shrink-0 ${expanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <div
        className={`overflow-hidden transition-all duration-300 ${
          expanded ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="px-6 pb-5 space-y-4 border-t border-card-border/30 pt-4">
          <p className="text-xs text-muted">{meta?.description}</p>
          {Object.entries(dimension.sub_factors).map(([key, sf]) => {
            const sfPct = sf.max > 0 ? (sf.score / sf.max) * 100 : 0;
            const evidenceLines = formatEvidence(sf.evidence);
            return (
              <div key={key} className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-foreground/80">{sf.label}</span>
                  <span className="font-mono text-muted">
                    {sf.score}/{sf.max}
                  </span>
                </div>
                <div className="h-1.5 bg-card-border/40 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${scoreBgGradient(sf.score, sf.max)}`}
                    style={{ width: `${sfPct}%` }}
                  />
                </div>
                {evidenceLines.length > 0 && (
                  <div className="text-xs text-muted/70 space-y-0.5 pl-3 border-l-2 border-card-border/50 ml-1">
                    {evidenceLines.map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ----- Scanning Animation -----

const SCAN_PHASES = [
  "Discovering endpoints...",
  "Checking MCP registries...",
  "Analyzing API documentation...",
  "Probing error structures...",
  "Testing agent compatibility...",
  "Evaluating trust signals...",
  "Calculating Clarvia Score...",
];

function ScanningView() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhase((p) => (p < SCAN_PHASES.length - 1 ? p + 1 : p));
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  const progress = ((phase + 1) / SCAN_PHASES.length) * 100;

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 px-6">
      <div className="w-full max-w-md space-y-4">
        <div className="h-1.5 bg-card-border/50 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
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
        <div className="flex justify-center pt-4">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    </div>
  );
}

// ----- Share Buttons -----

function ShareButtons({ result }: { result: ScanResult }) {
  const [copied, setCopied] = useState(false);

  function handleCopyUrl() {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleShareTwitter() {
    const text = `${result.service_name} scored ${result.clarvia_score}/100 on the Clarvia AEO Scanner! How agent-ready is your service?`;
    const url = window.location.href;
    window.open(
      `https://x.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
      "_blank"
    );
  }

  return (
    <div className="flex flex-wrap gap-3">
      <button
        onClick={handleCopyUrl}
        className="flex-1 min-w-[140px] glass-card hover:border-accent/30 text-foreground px-5 py-3 rounded-xl text-sm font-medium transition-all text-center inline-flex items-center justify-center gap-2"
      >
        {copied ? (
          <>
            <svg className="w-4 h-4 text-score-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            Copied!
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m9.86-3.07a4.5 4.5 0 00-1.242-7.244l-4.5-4.5a4.5 4.5 0 00-6.364 6.364L5.25 9" />
            </svg>
            Copy link
          </>
        )}
      </button>
      <button
        onClick={handleShareTwitter}
        className="flex-1 min-w-[140px] glass-card hover:border-accent/30 text-foreground px-5 py-3 rounded-xl text-sm font-medium transition-all text-center inline-flex items-center justify-center gap-2"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
        Share on X
      </button>
    </div>
  );
}

// ----- Main Results Page -----

export default function ScanResultPage() {
  const params = useParams();
  const scanId = params.id as string;

  const [result, setResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [appeared, setAppeared] = useState(false);

  useEffect(() => {
    if (!scanId) return;

    async function fetchResult() {
      try {
        const res = await fetch(`${API_BASE}/api/scan/${scanId}`);
        if (res.ok) {
          const data = await res.json();
          setResult(data);
          requestAnimationFrame(() => setAppeared(true));
          return;
        }

        const fallbackRes = await fetch("/data/prebuilt-scans.json");
        if (!fallbackRes.ok) throw new Error(`Failed to load scan (${res.status})`);
        const scans: ScanResult[] = await fallbackRes.json();
        const match = scans.find((s) => s.scan_id === scanId);
        if (!match) throw new Error(`Scan not found (${scanId})`);

        if (!match.top_recommendations) match.top_recommendations = [];
        if (!match.scan_duration_ms) match.scan_duration_ms = 0;
        if (!match.onchain_bonus) {
          match.onchain_bonus = { score: 0, max: 10, applicable: false, sub_factors: {} };
        }

        setResult(match);
        requestAnimationFrame(() => setAppeared(true));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load scan");
      } finally {
        setLoading(false);
      }
    }

    fetchResult();
  }, [scanId]);

  async function handleGetReport() {
    if (!result) return;
    setCheckoutLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/report/create-checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scan_id: result.scan_id }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "Failed to create checkout");
      }

      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Payment unavailable");
      setCheckoutLoading(false);
    }
  }

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
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">
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

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12">
        {loading && <ScanningView />}

        {error && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-score-red/10 flex items-center justify-center mb-2">
              <svg className="w-8 h-8 text-score-red" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <p className="text-score-red font-mono text-sm">{error}</p>
            <Link
              href="/"
              className="text-accent hover:text-accent-hover text-sm transition-colors"
            >
              Back to scanner
            </Link>
          </div>
        )}

        {result && (
          <div
            className={`space-y-10 transition-all duration-700 ${
              appeared ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            {/* Service header */}
            <div className="text-center space-y-3">
              <h1 className="text-3xl font-bold">{result.service_name}</h1>
              <p className="text-sm text-muted font-mono">{result.url}</p>
            </div>

            {/* Score + Grade */}
            <div className="flex flex-col items-center space-y-5">
              <ScoreGauge score={result.clarvia_score} />
              <span
                className={`inline-block px-4 py-1.5 rounded-xl border text-xs font-mono uppercase tracking-wider ${gradeBadgeClass(result.rating)}`}
              >
                {result.rating}
              </span>
              <p className="text-xs text-muted/60 italic text-center max-w-md mx-auto pt-2">
                Clarvia Score does not measure a company&apos;s size or quality.
                It measures how easily AI agents can discover and use this service.
              </p>
            </div>

            {/* Dimensions */}
            <div className="space-y-4">
              <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
                Dimensions
              </h2>
              {Object.entries(result.dimensions).map(([key, dim]) => (
                <DimensionBar key={key} dimKey={key} dimension={dim} />
              ))}
            </div>

            {/* Onchain bonus */}
            {result.onchain_bonus && (
              <div className="space-y-4">
                <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
                  Onchain Bonus
                </h2>
                <div className="glass-card rounded-xl px-6 py-5">
                  {result.onchain_bonus.applicable ? (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span>Onchain Score</span>
                        <span className="font-mono text-muted">
                          {result.onchain_bonus.score}/{result.onchain_bonus.max}
                        </span>
                      </div>
                      <div className="h-2.5 bg-card-border/40 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${scoreBgGradient(result.onchain_bonus.score, result.onchain_bonus.max)}`}
                          style={{
                            width: `${(result.onchain_bonus.score / result.onchain_bonus.max) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted">
                      Not applicable for this service. Onchain bonus applies to
                      services with blockchain integrations.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {result.top_recommendations.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
                  Top Recommendations
                </h2>
                <div className="space-y-3">
                  {result.top_recommendations.map((rec, i) => (
                    <div
                      key={i}
                      className={`rounded-xl px-6 py-4 flex gap-4 items-start border transition-all duration-200 hover:-translate-y-0.5 ${priorityBgClass(i)}`}
                    >
                      <span
                        className={`font-mono text-xs font-bold shrink-0 mt-0.5 ${priorityColorClass(i)}`}
                      >
                        {priorityIcon(i)}
                      </span>
                      <p className="text-sm leading-relaxed">{rec}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Share + Actions */}
            <div className="space-y-4">
              <h2 className="text-xs font-mono text-accent uppercase tracking-widest">Share</h2>
              <ShareButtons result={result} />
            </div>

            {/* Report CTA */}
            <div className="glass-card rounded-xl px-6 py-6 space-y-4">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold mb-1">Unlock the full report</p>
                  <ul className="text-xs text-muted space-y-1">
                    <li>All 13 sub-factors with detailed evidence</li>
                    <li>15 prioritized recommendations with implementation steps</li>
                    <li>Competitive benchmark data</li>
                    <li>Downloadable PDF report</li>
                  </ul>
                </div>
              </div>
              <button
                onClick={handleGetReport}
                disabled={checkoutLoading}
                className="w-full btn-gradient text-white px-5 py-3.5 rounded-xl text-sm font-medium text-center"
              >
                {checkoutLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Redirecting...
                  </span>
                ) : (
                  "Get Detailed Report — $29"
                )}
              </button>
            </div>

            {/* Metadata */}
            <div className="text-center text-xs text-muted/40 font-mono space-y-1 pb-6">
              <p>
                Scanned at{" "}
                {new Date(result.scanned_at).toLocaleString("en-US", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
              {result.scan_duration_ms > 0 && (
                <p>Scan duration: {(result.scan_duration_ms / 1000).toFixed(1)}s</p>
              )}
            </div>
          </div>
        )}
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
