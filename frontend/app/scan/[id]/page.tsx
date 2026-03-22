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

function scoreBgClass(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bg-score-green";
  if (pct >= 0.4) return "bg-score-yellow";
  return "bg-score-red";
}

function gradeBadgeClass(rating: string): string {
  switch (rating) {
    case "Exceptional":
    case "Strong":
      return "bg-score-green/15 text-score-green border-score-green/30";
    case "Moderate":
    case "Good":
      return "bg-score-yellow/15 text-score-yellow border-score-yellow/30";
    case "Basic":
      return "bg-score-yellow/15 text-score-yellow border-score-yellow/30";
    default:
      return "bg-score-red/15 text-score-red border-score-red/30";
  }
}

const DIMENSION_LABELS: Record<string, { label: string; description: string }> =
  {
    api_accessibility: {
      label: "API Accessibility",
      description: "How easily agents can reach and authenticate with your API",
    },
    data_structuring: {
      label: "Data Structuring",
      description: "Schema definition, pricing clarity, and error handling",
    },
    agent_compatibility: {
      label: "Agent Compatibility",
      description: "MCP support, robot policies, and discovery mechanisms",
    },
    trust_signals: {
      label: "Trust Signals",
      description: "Uptime, documentation quality, and update frequency",
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
      // Ease-out cubic
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

  return (
    <div className="relative w-40 h-40 mx-auto">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke="#1e2a3a"
          strokeWidth="8"
        />
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          className="transition-[stroke] duration-300"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="text-4xl font-mono font-bold transition-[color] duration-300"
          style={{ color }}
        >
          {animatedScore}
        </span>
        <span className="text-xs text-muted mt-1">/ 100</span>
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
  const meta = DIMENSION_LABELS[dimKey];
  const pct = dimension.max > 0 ? (dimension.score / dimension.max) * 100 : 0;

  return (
    <div className="bg-card-bg border border-card-border rounded-lg overflow-hidden transition-all duration-300">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 text-left flex items-center gap-4 hover:bg-card-border/20 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">{meta?.label || dimKey}</span>
            <span className="font-mono text-sm text-muted">
              {dimension.score}/{dimension.max}
            </span>
          </div>
          <div className="h-2 bg-card-border rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${scoreBgClass(dimension.score, dimension.max)}`}
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
        <div className="px-5 pb-4 space-y-3 border-t border-card-border pt-3">
          <p className="text-xs text-muted">{meta?.description}</p>
          {Object.entries(dimension.sub_factors).map(([key, sf]) => {
            const sfPct = sf.max > 0 ? (sf.score / sf.max) * 100 : 0;
            const evidenceLines = formatEvidence(sf.evidence);
            return (
              <div key={key} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-foreground/80">{sf.label}</span>
                  <span className="font-mono text-muted">
                    {sf.score}/{sf.max}
                  </span>
                </div>
                <div className="h-1.5 bg-card-border rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${scoreBgClass(sf.score, sf.max)}`}
                    style={{ width: `${sfPct}%` }}
                  />
                </div>
                {evidenceLines.length > 0 && (
                  <div className="text-xs text-muted/70 space-y-0.5 pl-2 border-l border-card-border">
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
        <div className="h-1.5 bg-card-border rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
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

// ----- Main Results Page -----

export default function ScanResultPage() {
  const params = useParams();
  const scanId = params.id as string;

  const [result, setResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [appeared, setAppeared] = useState(false);

  useEffect(() => {
    if (!scanId) return;

    async function fetchResult() {
      try {
        const res = await fetch(`${API_BASE}/api/scan/${scanId}`);
        if (!res.ok) throw new Error(`Failed to load scan (${res.status})`);
        const data = await res.json();
        setResult(data);
        // Trigger entrance animation
        requestAnimationFrame(() => setAppeared(true));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load scan");
      } finally {
        setLoading(false);
      }
    }

    fetchResult();
  }, [scanId]);

  function handleCopyUrl() {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

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
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-card-border px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link
            href="/"
            className="font-mono text-sm tracking-widest text-muted uppercase hover:text-foreground transition-colors"
          >
            Clarvia
          </Link>
          <span className="text-xs text-muted">AEO Scanner v1.0</span>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-10">
        {loading && <ScanningView />}

        {error && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
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
            className={`space-y-8 transition-all duration-700 ${
              appeared ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            {/* Service header */}
            <div className="text-center space-y-2">
              <h1 className="text-2xl font-bold">{result.service_name}</h1>
              <p className="text-sm text-muted font-mono">{result.url}</p>
            </div>

            {/* Score + Grade */}
            <div className="flex flex-col items-center space-y-4">
              <ScoreGauge score={result.clarvia_score} />
              <span
                className={`inline-block px-3 py-1 rounded-full border text-xs font-mono uppercase tracking-wider ${gradeBadgeClass(result.rating)}`}
              >
                {result.rating}
              </span>
            </div>

            {/* Dimensions */}
            <div className="space-y-3">
              <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
                Dimensions
              </h2>
              {Object.entries(result.dimensions).map(([key, dim]) => (
                <DimensionBar key={key} dimKey={key} dimension={dim} />
              ))}
            </div>

            {/* Onchain bonus */}
            {result.onchain_bonus && (
              <div className="space-y-3">
                <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
                  Onchain Bonus
                </h2>
                <div className="bg-card-bg border border-card-border rounded-lg px-5 py-4">
                  {result.onchain_bonus.applicable ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>Onchain Score</span>
                        <span className="font-mono text-muted">
                          {result.onchain_bonus.score}/{result.onchain_bonus.max}
                        </span>
                      </div>
                      <div className="h-2 bg-card-border rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${scoreBgClass(result.onchain_bonus.score, result.onchain_bonus.max)}`}
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
              <div className="space-y-3">
                <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
                  Top Recommendations
                </h2>
                <div className="space-y-2">
                  {result.top_recommendations.map((rec, i) => (
                    <div
                      key={i}
                      className="bg-card-bg border border-card-border rounded-lg px-5 py-3 flex gap-3 items-start"
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

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <button
                onClick={handleCopyUrl}
                className="flex-1 bg-card-bg border border-card-border hover:border-accent/50 text-foreground px-5 py-3 rounded-lg text-sm font-medium transition-colors text-center"
              >
                {copied ? "Copied!" : "Share this score"}
              </button>
              <button
                onClick={handleGetReport}
                disabled={checkoutLoading}
                className="flex-1 bg-accent hover:bg-accent-hover disabled:opacity-60 text-white px-5 py-3 rounded-lg text-sm font-medium transition-colors text-center"
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

            {/* Report upsell */}
            <div className="bg-card-bg border border-card-border rounded-lg px-5 py-4 space-y-2">
              <p className="text-sm font-medium">
                Unlock the full report
              </p>
              <ul className="text-xs text-muted space-y-1">
                <li>All 13 sub-factors with detailed evidence</li>
                <li>15 prioritized recommendations with implementation steps</li>
                <li>Competitive benchmark data</li>
                <li>Downloadable PDF report</li>
              </ul>
            </div>

            {/* Metadata */}
            <div className="text-center text-xs text-muted/50 font-mono space-y-1 pb-6">
              <p>
                Scanned at{" "}
                {new Date(result.scanned_at).toLocaleString("en-US", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
              <p>Scan duration: {(result.scan_duration_ms / 1000).toFixed(1)}s</p>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border px-6 py-6">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted">
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
