"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";
import Nav from "@/app/components/Nav";

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
  agent_grade?: string;
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

function scoreInterpretation(score: number): string {
  if (score >= 80) return "Excellent — AI agents can fully discover and use this service with minimal friction.";
  if (score >= 60) return "Good — Agents can use this service, but some areas need improvement for seamless integration.";
  if (score >= 40) return "Needs Work — Agents face notable barriers. Focus on the top recommendations below.";
  return "Poor — Agents cannot effectively discover or use this service yet. Major improvements needed.";
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

function agentGradeMeta(grade: string): { label: string; colorClass: string; description: string } {
  switch (grade) {
    case "AGENT_NATIVE":
      return { label: "Agent Native", colorClass: "bg-score-green/10 text-score-green border-score-green/20", description: "Built for AI agents — full discovery, auth, and tool compatibility" };
    case "AGENT_FRIENDLY":
      return { label: "Agent Friendly", colorClass: "bg-accent/10 text-accent border-accent/20", description: "Agents can integrate with moderate effort" };
    case "AGENT_POSSIBLE":
      return { label: "Agent Possible", colorClass: "bg-score-yellow/10 text-score-yellow border-score-yellow/20", description: "Basic agent use possible, but significant friction remains" };
    case "AGENT_HOSTILE":
      return { label: "Agent Hostile", colorClass: "bg-score-red/10 text-score-red border-score-red/20", description: "Agents cannot reliably discover or use this service" };
    default:
      return { label: grade, colorClass: "bg-card-border/20 text-muted border-card-border", description: "" };
  }
}

const DIMENSION_META: Record<string, {
  label: string;
  description: string;
  color: string;
  iconColor: string;
  beginnerTip: string;
  scoreHints: { low: string; mid: string; high: string };
}> = {
  api_accessibility: {
    label: "API Accessibility",
    description: "How easily agents can reach and authenticate with your API",
    color: "blue",
    iconColor: "text-blue-400",
    beginnerTip: "Can AI agents find a clear entrance to this service? This checks for API docs, CORS headers, and authentication.",
    scoreHints: {
      low: "Agents struggle to find or connect to this API. Adding OpenAPI docs and CORS headers would help.",
      mid: "Basic access works, but authentication or documentation could be clearer for agents.",
      high: "Agents can easily discover and connect to this API.",
    },
  },
  data_structuring: {
    label: "Data Structuring",
    description: "Schema definition, pricing clarity, and error handling",
    color: "purple",
    iconColor: "text-purple-400",
    beginnerTip: "When agents get data back, is it well-organized? This checks for clear schemas, error messages, and pricing info.",
    scoreHints: {
      low: "Responses lack clear structure. Agents may misinterpret the data without proper schemas.",
      mid: "Data is partially structured, but some responses lack schemas or clear error formats.",
      high: "Clean, well-documented data structures that agents can parse reliably.",
    },
  },
  agent_compatibility: {
    label: "Agent Compatibility",
    description: "MCP support, robot policies, and discovery mechanisms",
    color: "cyan",
    iconColor: "text-cyan-400",
    beginnerTip: "Is this service built with AI agents in mind? This checks for MCP support, robot-friendly policies, and discovery features.",
    scoreHints: {
      low: "No agent-specific features detected. Adding MCP support or an agent-friendly robots.txt would help.",
      mid: "Some agent features exist, but full MCP support or discovery mechanisms are missing.",
      high: "Strong agent support with MCP, clear robot policies, and easy discovery.",
    },
  },
  trust_signals: {
    label: "Trust Signals",
    description: "Uptime, documentation quality, and update frequency",
    color: "emerald",
    iconColor: "text-emerald-400",
    beginnerTip: "Can agents trust this service to be reliable? This checks uptime, documentation quality, and how often it's updated.",
    scoreHints: {
      low: "Limited reliability signals. Agents may hesitate to depend on this service.",
      mid: "Some trust signals present, but documentation or uptime could be improved.",
      high: "Highly reliable with strong docs, good uptime, and regular updates.",
    },
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

function subFactorStatus(sf: SubFactor): { icon: "check" | "warn" | "x"; color: string; bgColor: string } {
  const pct = sf.max > 0 ? sf.score / sf.max : 0;
  if (pct >= 0.7) return { icon: "check", color: "text-score-green", bgColor: "bg-score-green/5" };
  if (pct >= 0.3) return { icon: "warn", color: "text-score-yellow", bgColor: "bg-score-yellow/5" };
  return { icon: "x", color: "text-score-red", bgColor: "bg-score-red/5" };
}

function StatusIcon({ type, className }: { type: "check" | "warn" | "x"; className?: string }) {
  if (type === "check") return <svg className={className || "w-4 h-4"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>;
  if (type === "warn") return <svg className={className || "w-4 h-4"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>;
  return <svg className={className || "w-4 h-4"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>;
}

function subFactorSummary(sf: SubFactor): string {
  const ev = sf.evidence || {};
  // Try to derive a human-readable summary from evidence
  if (typeof ev.reason === "string") return ev.reason;
  if (typeof ev.p50_ms === "number") return `Median response: ${ev.p50_ms}ms`;
  if (typeof ev.status === "number") return `HTTP ${ev.status}`;
  if (typeof ev.endpoint === "string") return `Endpoint: ${(ev.endpoint as string).replace(/^https?:\/\//, "")}`;
  if (typeof ev.spec_url === "string") return `Spec found`;
  if (Array.isArray(ev.keywords_found) && ev.keywords_found.length > 0)
    return `Keywords: ${(ev.keywords_found as string[]).slice(0, 3).join(", ")}`;
  if (Array.isArray(ev.indicators) && ev.indicators.length > 0)
    return `${(ev.indicators as string[]).slice(0, 2).join(", ")}`;
  // Fallback: score description
  const pct = sf.max > 0 ? sf.score / sf.max : 0;
  if (pct >= 0.7) return "Strong performance";
  if (pct >= 0.3) return "Partial coverage";
  return "Not detected";
}

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

  // Pick top 3 sub-factors to show as highlights (sorted by impact: lowest ratio first to show issues)
  const subEntries = Object.entries(dimension.sub_factors || {});
  const highlights = [...subEntries]
    .sort((a, b) => {
      const ratioA = a[1].max > 0 ? a[1].score / a[1].max : 0;
      const ratioB = b[1].max > 0 ? b[1].score / b[1].max : 0;
      // Show mixed: best first, then worst, to give a balanced view
      return ratioB - ratioA;
    })
    .slice(0, 3);

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
              {meta?.beginnerTip && (
                <span className="group relative">
                  <span className="cursor-help text-muted/50 hover:text-muted text-xs">[?]</span>
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 rounded-xl bg-card-bg border border-card-border text-xs text-muted leading-relaxed opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity z-50 shadow-lg">
                    {meta.beginnerTip}
                  </span>
                </span>
              )}
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
          {/* Score interpretation hint */}
          {meta?.scoreHints && (
            <p className="mt-2 text-xs text-muted/70 leading-relaxed">
              {pct >= 70 ? meta.scoreHints.high : pct >= 30 ? meta.scoreHints.mid : meta.scoreHints.low}
            </p>
          )}
          {/* Sub-factor highlights — always visible */}
          {highlights.length > 0 && (
            <div className="mt-3 space-y-1.5">
              {highlights.map(([key, sf]) => {
                const status = subFactorStatus(sf);
                const summary = subFactorSummary(sf);
                return (
                  <div key={key} className={`flex items-center gap-2 text-xs rounded-lg px-2 py-1 ${status.bgColor}`}>
                    <StatusIcon type={status.icon} className={`shrink-0 w-3.5 h-3.5 ${status.color}`} />
                    <span className={`font-medium ${status.color}`}>{sf.label}</span>
                    <span className="text-muted/70 truncate">{summary}</span>
                  </div>
                );
              })}
            </div>
          )}
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
          {Object.entries(dimension.sub_factors || {}).map(([key, sf]) => {
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
                  <div className="relative">
                    <div className="text-xs text-muted/70 space-y-0.5 pl-3 border-l-2 border-card-border/50 ml-1 blur-[3px] select-none">
                      {evidenceLines.map((line, i) => (
                        <p key={i}>{line}</p>
                      ))}
                    </div>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-xs text-accent bg-background/80 px-3 py-1 rounded-lg border border-accent/20">
                        Evidence in full report
                      </span>
                    </div>
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

// ----- Score History (server API + localStorage fallback) -----

interface HistoryEntry {
  score: number;
  date: string;
}

function getLocalHistory(url: string): HistoryEntry[] {
  try {
    const key = `clarvia_history_${url}`;
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveLocalHistory(url: string, currentScore: number) {
  try {
    const key = `clarvia_history_${url}`;
    const existing = getLocalHistory(url);
    const now = new Date().toISOString();
    if (!existing.length || existing[existing.length - 1].score !== currentScore) {
      existing.push({ score: currentScore, date: now });
      const trimmed = existing.slice(-10);
      localStorage.setItem(key, JSON.stringify(trimmed));
    }
  } catch {
    // localStorage unavailable
  }
}

function useScanHistory(url: string, currentScore: number) {
  const [previousScore, setPreviousScore] = useState<number | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    if (!url || !currentScore) return;

    let cancelled = false;

    async function loadHistory() {
      // Always save to localStorage for offline support
      saveLocalHistory(url, currentScore);

      // Try server API first
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/history?url=${encodeURIComponent(url)}&limit=10`
        );
        if (res.ok) {
          const data = await res.json();
          const entries: HistoryEntry[] = Array.isArray(data)
            ? data.map((d: { clarvia_score?: number; score?: number; scanned_at?: string; date?: string }) => ({
                score: d.clarvia_score ?? d.score ?? 0,
                date: d.scanned_at ?? d.date ?? "",
              }))
            : Array.isArray(data?.items)
              ? data.items.map((d: { clarvia_score?: number; score?: number; scanned_at?: string; date?: string }) => ({
                  score: d.clarvia_score ?? d.score ?? 0,
                  date: d.scanned_at ?? d.date ?? "",
                }))
              : [];

          if (!cancelled && entries.length > 0) {
            setHistory(entries);
            // Find the entry before the current scan
            const previous = entries.filter((e) => e.score !== currentScore);
            if (previous.length > 0) {
              setPreviousScore(previous[previous.length - 1].score);
            }
            return;
          }
        }
      } catch {
        // Server unavailable — fall through to localStorage
      }

      // Fallback: localStorage
      if (!cancelled) {
        const local = getLocalHistory(url);
        setHistory(local);
        const prev = local.filter((e) => e.score !== currentScore);
        if (prev.length > 0) {
          setPreviousScore(prev[prev.length - 1].score);
        }
      }
    }

    loadHistory();
    return () => { cancelled = true; };
  }, [url, currentScore]);

  return { previousScore, history };
}

// ----- Percentile Hook (Data Moat B) -----

function usePercentile(url: string) {
  const [data, setData] = useState<{
    percentile: number;
    rank: number;
    total: number;
  } | null>(null);

  useEffect(() => {
    if (!url) return;
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/benchmark/percentile?url=${encodeURIComponent(url)}`
        );
        if (res.ok) {
          const json = await res.json();
          if (!cancelled && json.percentile !== undefined) {
            setData({
              percentile: json.percentile,
              rank: json.rank,
              total: json.total_services,
            });
          }
        }
      } catch {
        // Benchmark data not available yet
      }
    }

    load();
    return () => { cancelled = true; };
  }, [url]);

  return data;
}

// ----- Percentile Badge -----

function PercentileBadge({ percentile, rank, total }: { percentile: number; rank: number; total: number }) {
  const color =
    percentile >= 75 ? "text-score-green border-score-green/20 bg-score-green/10" :
    percentile >= 50 ? "text-accent border-accent/20 bg-accent/10" :
    percentile >= 25 ? "text-score-yellow border-score-yellow/20 bg-score-yellow/10" :
    "text-muted border-card-border bg-card-bg";

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-mono ${color}`}>
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
      </svg>
      Top {Math.round(100 - percentile)}% · #{rank} of {total}
    </span>
  );
}

// ----- Mini Trend Chart (SVG sparkline) -----

function MiniTrendChart({ scores }: { scores: number[] }) {
  if (scores.length < 2) return null;

  const w = 120;
  const h = 32;
  const pad = 4;
  const min = Math.min(...scores) - 5;
  const max = Math.max(...scores) + 5;
  const range = max - min || 1;

  const points = scores.map((s, i) => {
    const x = pad + (i / (scores.length - 1)) * (w - pad * 2);
    const y = h - pad - ((s - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  });

  const last = scores[scores.length - 1];
  const first = scores[0];
  const color = last >= first ? "#22c55e" : "#ef4444";

  return (
    <svg width={w} height={h} className="mt-1 opacity-80">
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {scores.map((s, i) => {
        const x = pad + (i / (scores.length - 1)) * (w - pad * 2);
        const y = h - pad - ((s - min) / range) * (h - pad * 2);
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r={i === scores.length - 1 ? 3 : 2}
            fill={i === scores.length - 1 ? color : "transparent"}
            stroke={color}
            strokeWidth="1.5"
          />
        );
      })}
    </svg>
  );
}

// ----- Agent Probe Section (Data Moat C) -----

interface ProbeResult {
  probe_score: number;
  probe_rating: string;
  agent_access: {
    reachable: boolean;
    status_code?: number;
    latency_ms?: number;
    blocked?: boolean;
  };
  robots_policy: {
    exists: boolean;
    ai_agent_mentions: string[];
    allows_ai: boolean;
  };
  discovery_endpoints: Record<string, { found: boolean; status: number }>;
  structured_data: {
    json_available: boolean;
  };
}

function useAgentProbe(url: string) {
  const [data, setData] = useState<ProbeResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runProbe = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/accessibility-probe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (res.ok) {
        setData(await res.json());
      }
    } catch {
      // probe not available
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, runProbe };
}

function AgentProbeSection({ url }: { url: string }) {
  const { data, loading, runProbe } = useAgentProbe(url);

  if (!data) {
    return (
      <div className="glass-card rounded-xl px-6 py-5 text-center">
        <h3 className="text-xs font-mono text-accent uppercase tracking-widest mb-3">
          Agent Accessibility Probe
        </h3>
        <p className="text-sm text-muted mb-4">
          Test how AI agents actually experience this service
        </p>
        <button
          onClick={runProbe}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-accent/10 text-accent text-sm font-medium hover:bg-accent/20 transition-colors disabled:opacity-50"
        >
          {loading ? "Probing..." : "Run Agent Probe"}
        </button>
      </div>
    );
  }

  const checks = [
    {
      label: "Agent Reachable",
      pass: data.agent_access.reachable && !data.agent_access.blocked,
      detail: data.agent_access.latency_ms ? `${data.agent_access.latency_ms}ms` : "N/A",
    },
    {
      label: "AI Allowed (robots.txt)",
      pass: data.robots_policy.allows_ai,
      detail: data.robots_policy.exists ? "Policy found" : "No robots.txt",
    },
    {
      label: "Discovery Endpoints",
      pass: Object.values(data.discovery_endpoints).some((e) => e.found),
      detail: `${Object.values(data.discovery_endpoints).filter((e) => e.found).length}/5 found`,
    },
    {
      label: "Structured Data (JSON)",
      pass: data.structured_data.json_available,
      detail: data.structured_data.json_available ? "Available" : "HTML only",
    },
  ];

  const probeColor =
    data.probe_score >= 80 ? "text-score-green" :
    data.probe_score >= 60 ? "text-accent" :
    data.probe_score >= 40 ? "text-score-yellow" :
    "text-score-red";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
          Agent Accessibility Probe
        </h2>
        <span className={`text-sm font-mono font-bold ${probeColor}`}>
          {data.probe_score}/100 · {data.probe_rating}
        </span>
      </div>
      <div className="glass-card rounded-xl px-6 py-5 space-y-3">
        {checks.map((c, i) => (
          <div key={i} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span className={c.pass ? "text-score-green" : "text-score-red"}>
                <StatusIcon type={c.pass ? "check" : "x"} className="w-3.5 h-3.5" />
              </span>
              <span>{c.label}</span>
            </div>
            <span className="text-xs text-muted font-mono">{c.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ----- Score Delta Badge -----

function ScoreDelta({
  previous,
  current,
  history,
}: {
  previous: number;
  current: number;
  history: HistoryEntry[];
}) {
  const delta = current - previous;

  // Find the last scan date from history (the entry before current)
  const prevEntries = history.filter((e) => e.score !== current);
  const lastEntry = prevEntries.length > 0 ? prevEntries[prevEntries.length - 1] : null;

  function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    if (days === 0) return "today";
    if (days === 1) return "1 day ago";
    if (days < 30) return `${days} days ago`;
    const months = Math.floor(days / 30);
    return months === 1 ? "1 month ago" : `${months} months ago`;
  }

  // Build trend line from history (unique scores in order)
  const trend = history.length >= 2
    ? history.slice(-5).map((e) => e.score)
    : null;

  return (
    <div className="flex flex-col items-center gap-1.5">
      {delta !== 0 && (
        <span
          className={`inline-flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded-lg ${
            delta > 0
              ? "bg-score-green/10 text-score-green border border-score-green/20"
              : "bg-score-red/10 text-score-red border border-score-red/20"
          }`}
        >
          {delta > 0 ? "↑" : "↓"} {delta > 0 ? "+" : ""}{delta} from last scan
        </span>
      )}
      {lastEntry?.date && (
        <span className="text-[10px] text-muted/60 font-mono">
          Last scanned: {timeAgo(lastEntry.date)} (score: {lastEntry.score})
        </span>
      )}
      {trend && trend.length >= 2 && (
        <MiniTrendChart scores={trend} />
      )}
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
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
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

// ----- Improvement Playbook Section -----

interface PlaybookItem {
  sub_factor: string;
  dimension: string;
  label: string;
  current_score: number;
  max_score: number;
  potential_gain: number;
  fixes: Record<string, { title: string; code: string; install: string; estimated_time: string }>;
}

function PlaybookSection({ scanId }: { scanId: string }) {
  const [items, setItems] = useState<PlaybookItem[]>([]);
  const [totalGain, setTotalGain] = useState(0);
  const [projectedScore, setProjectedScore] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [stack, setStack] = useState<"python" | "nodejs" | "go">("python");
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/playbook?scan_id=${encodeURIComponent(scanId)}`)
      .then((r) => r.json())
      .then((data) => {
        setItems(data.items || []);
        setTotalGain(data.total_potential_gain || 0);
        setProjectedScore(data.projected_score || 0);
      })
      .catch(console.warn)
      .finally(() => setLoaded(true));
  }, [scanId]);

  function handleCopy(code: string, key: string) {
    navigator.clipboard.writeText(code);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  }

  if (!loaded || items.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-mono text-accent uppercase tracking-widest flex items-center gap-2">
          Improvement Playbook
          <span className="text-xs font-bold text-score-green">+{totalGain} pts possible</span>
        </h2>
        {/* Stack selector */}
        <div className="flex gap-1">
          {(["python", "nodejs", "go"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStack(s)}
              className={`text-[10px] font-mono px-2 py-1 rounded border transition-colors cursor-pointer ${
                stack === s ? "border-accent/50 text-accent bg-accent/5" : "border-card-border text-muted hover:border-accent/30"
              }`}
            >
              {s === "nodejs" ? "Node.js" : s === "python" ? "Python" : "Go"}
            </button>
          ))}
        </div>
      </div>

      {/* Projected score bar */}
      <div className="glass-card rounded-xl px-6 py-3 flex items-center gap-4">
        <span className="text-[10px] text-muted font-mono">PROJECTED SCORE</span>
        <div className="flex-1 h-2 bg-card-border/30 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-score-green/60 transition-all"
            style={{ width: `${projectedScore}%` }}
          />
        </div>
        <span className="text-sm font-mono font-bold text-score-green">{projectedScore}</span>
      </div>

      {/* Playbook items */}
      <div className="space-y-2">
        {items.map((item) => {
          const isOpen = expanded === item.sub_factor;
          const fix = item.fixes[stack];
          return (
            <div key={item.sub_factor} className="glass-card rounded-xl overflow-hidden">
              <button
                onClick={() => setExpanded(isOpen ? null : item.sub_factor)}
                className="w-full px-5 py-3 flex items-center gap-3 text-left cursor-pointer hover:bg-white/[0.02] transition-colors"
              >
                <span className="text-xs font-bold text-score-green font-mono w-10">
                  +{item.potential_gain}
                </span>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium">{item.label}</span>
                  <span className="text-[10px] text-muted/50 font-mono ml-2">
                    {item.current_score}/{item.max_score}
                  </span>
                </div>
                <span className="text-[10px] text-muted/40 font-mono capitalize">{item.dimension.replace(/_/g, " ")}</span>
                <svg
                  className={`w-4 h-4 text-muted/40 transition-transform ${isOpen ? "rotate-180" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {isOpen && fix && (
                <div className="px-5 pb-4 space-y-3 border-t border-card-border/20 pt-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{fix.title}</span>
                    <span className="text-[10px] text-muted font-mono">{fix.estimated_time}</span>
                  </div>
                  {fix.install && (
                    <div className="flex items-center gap-2">
                      <code className="text-[10px] font-mono px-2 py-1 bg-black/30 rounded text-accent/70">
                        {fix.install}
                      </code>
                    </div>
                  )}
                  <div className="relative">
                    <pre className="bg-black/40 rounded-lg p-4 text-[11px] font-mono leading-relaxed overflow-x-auto max-h-64 text-muted/80">
                      {fix.code}
                    </pre>
                    <button
                      onClick={() => handleCopy(fix.code, item.sub_factor)}
                      className="absolute top-2 right-2 text-[10px] px-2 py-1 rounded bg-card-border/50 hover:bg-accent/20 transition-colors cursor-pointer"
                    >
                      {copied === item.sub_factor ? "Copied!" : "Copy"}
                    </button>
                  </div>
                </div>
              )}
              {isOpen && !fix && (
                <div className="px-5 pb-4 border-t border-card-border/20 pt-3">
                  <p className="text-xs text-muted">No {stack === "nodejs" ? "Node.js" : stack} template available. Try another stack.</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ----- History & Trends Section -----

interface HistoryScan {
  scan_id: string;
  score: number;
  rating: string;
  scanned_at: string;
  dimensions?: Record<string, number>;
}

function HistorySection({
  url,
  currentScore,
  currentDimensions,
}: {
  url: string;
  currentScore: number;
  currentDimensions: Record<string, Dimension>;
}) {
  const [history, setHistory] = useState<HistoryScan[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [rescanning, setRescanning] = useState(false);

  useEffect(() => {
    if (!url) return;
    fetch(`${API_BASE}/api/v1/history?url=${encodeURIComponent(url)}&limit=10`)
      .then((r) => r.json())
      .then((data) => {
        const scans = data.scans || data.items || [];
        setHistory(scans);
      })
      .catch(console.warn)
      .finally(() => setLoaded(true));
  }, [url]);

  async function handleRescan() {
    setRescanning(true);
    try {
      const res = await fetch(`${API_BASE}/api/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.scan_id) {
          window.location.href = `/scan/${data.scan_id}`;
          return;
        }
      }
    } catch {}
    setRescanning(false);
  }

  if (!loaded) return null;

  // Need at least 1 previous scan to show history
  const prevScans = history.filter((h) => h.score !== currentScore || history.length > 1);
  if (prevScans.length === 0 && history.length <= 1) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            History
          </h2>
          <button
            onClick={handleRescan}
            disabled={rescanning}
            className="text-xs px-3 py-1.5 rounded-lg border border-card-border hover:border-accent/30 transition-colors disabled:opacity-50"
          >
            {rescanning ? "Scanning..." : "Rescan now"}
          </button>
        </div>
        <div className="glass-card rounded-xl px-6 py-4 text-center">
          <p className="text-xs text-muted">First scan for this URL. Rescan later to track changes.</p>
        </div>
      </div>
    );
  }

  const sorted = [...history].sort(
    (a, b) => new Date(a.scanned_at).getTime() - new Date(b.scanned_at).getTime()
  );
  const prev = sorted.length >= 2 ? sorted[sorted.length - 2] : null;
  const scoreDelta = prev ? currentScore - prev.score : 0;

  // Simple SVG sparkline
  const maxScore = 100;
  const points = sorted.map((s, i) => {
    const x = sorted.length > 1 ? (i / (sorted.length - 1)) * 280 + 10 : 150;
    const y = 60 - (s.score / maxScore) * 50 + 5;
    return `${x},${y}`;
  });
  const polyline = points.join(" ");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-mono text-accent uppercase tracking-widest flex items-center gap-2">
          History
          {scoreDelta !== 0 && (
            <span className={`text-xs font-bold ${scoreDelta > 0 ? "text-score-green" : "text-score-red"}`}>
              {scoreDelta > 0 ? "+" : ""}{scoreDelta}
            </span>
          )}
        </h2>
        <button
          onClick={handleRescan}
          disabled={rescanning}
          className="text-xs px-3 py-1.5 rounded-lg border border-card-border hover:border-accent/30 transition-colors disabled:opacity-50 cursor-pointer"
        >
          {rescanning ? "Scanning..." : "Rescan now"}
        </button>
      </div>

      <div className="glass-card rounded-xl px-6 py-5">
        <div className="flex flex-col sm:flex-row gap-6">
          {/* Score timeline chart */}
          <div className="flex-1">
            <p className="text-[10px] text-muted font-mono mb-2">SCORE TREND ({sorted.length} scans)</p>
            <svg viewBox="0 0 300 70" className="w-full h-16">
              {/* Grid lines */}
              <line x1="10" y1="5" x2="290" y2="5" stroke="rgba(255,255,255,0.05)" />
              <line x1="10" y1="30" x2="290" y2="30" stroke="rgba(255,255,255,0.05)" />
              <line x1="10" y1="55" x2="290" y2="55" stroke="rgba(255,255,255,0.05)" />
              {/* Score line */}
              <polyline
                fill="none"
                stroke={scoreColor(currentScore)}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={polyline}
              />
              {/* Score dots */}
              {sorted.map((s, i) => {
                const x = sorted.length > 1 ? (i / (sorted.length - 1)) * 280 + 10 : 150;
                const y = 60 - (s.score / maxScore) * 50 + 5;
                return (
                  <circle
                    key={i}
                    cx={x}
                    cy={y}
                    r="3"
                    fill={scoreColor(s.score)}
                    stroke="rgba(0,0,0,0.3)"
                    strokeWidth="1"
                  />
                );
              })}
            </svg>
          </div>

          {/* Dimension diff (vs previous) */}
          {prev?.dimensions && (
            <div className="sm:w-48 space-y-2">
              <p className="text-[10px] text-muted font-mono">VS PREVIOUS SCAN</p>
              {Object.entries(currentDimensions).map(([key, dim]) => {
                const prevScore = prev.dimensions?.[key] ?? 0;
                const delta = dim.score - (typeof prevScore === "number" ? prevScore : 0);
                return (
                  <div key={key} className="flex items-center justify-between text-[11px]">
                    <span className="text-muted capitalize truncate">{DIMENSION_META[key]?.label || key}</span>
                    <span className={`font-mono font-bold ${delta > 0 ? "text-score-green" : delta < 0 ? "text-score-red" : "text-muted/50"}`}>
                      {delta > 0 ? "+" : ""}{delta}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Scan history list */}
        <div className="mt-4 pt-3 border-t border-card-border/20">
          <div className="flex flex-wrap gap-2">
            {sorted.map((s, i) => (
              <a
                key={s.scan_id}
                href={`/scan/${s.scan_id}`}
                className={`text-[10px] font-mono px-2 py-1 rounded border transition-colors ${
                  i === sorted.length - 1
                    ? "border-accent/40 text-accent bg-accent/5"
                    : "border-card-border/30 text-muted hover:border-accent/20"
                }`}
              >
                {new Date(s.scanned_at).toLocaleDateString("en", { month: "short", day: "numeric" })}
                {" "}
                <span className={`font-bold ${i === sorted.length - 1 ? "" : ""}`}>{s.score}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ----- Free Actions Section -----

function FreeActions({ result }: { result: ScanResult }) {
  const [badgeCopied, setBadgeCopied] = useState(false);
  const [badgeStyle, setBadgeStyle] = useState<"flat" | "flat-square">("flat");

  const badgeId = encodeURIComponent(result.scan_id || result.service_name);
  const badgeUrl = `${API_BASE}/api/badge/${badgeId}${badgeStyle !== "flat" ? `?style=${badgeStyle}` : ""}`;
  const detailsUrl = typeof window !== "undefined" ? window.location.href : `https://clarvia.art/scan/${result.scan_id}`;
  const badgeMarkdown = `[![AEO Score: ${result.clarvia_score}](${badgeUrl})](${detailsUrl})`;
  const badgeHtml = `<a href="${detailsUrl}"><img src="${badgeUrl}" alt="AEO Score: ${result.clarvia_score}" /></a>`;

  function handleCopyBadge(format: "md" | "html") {
    navigator.clipboard.writeText(format === "md" ? badgeMarkdown : badgeHtml);
    setBadgeCopied(true);
    setTimeout(() => setBadgeCopied(false), 2000);
  }

  function handleDownloadMiniReport() {
    const lines = [
      `CLARVIA AEO SCORE SUMMARY`,
      `========================`,
      ``,
      `Service: ${result.service_name}`,
      `URL: ${result.url}`,
      `Score: ${result.clarvia_score}/100 (${result.rating})`,
      `Scanned: ${new Date(result.scanned_at).toLocaleString()}`,
      ``,
      `DIMENSIONS`,
      `----------`,
      ...(result.dimensions ? Object.entries(result.dimensions).map(([key, dim]) => {
        const label = DIMENSION_META[key]?.label || key;
        return `${label}: ${dim.score}/${dim.max}`;
      }) : []),
      ``,
      `TOP RECOMMENDATIONS`,
      `-------------------`,
      ...result.top_recommendations.slice(0, 3).map((rec, i) => `${i + 1}. ${rec}`),
      ``,
      `---`,
      `Full report with 15 recommendations, code examples,`,
      `competitive benchmarks, and implementation roadmap:`,
      `${typeof window !== "undefined" ? window.location.href : ""}`,
      ``,
      `Generated by Clarvia AEO Scanner | clarvia.art`,
    ];

    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `clarvia-summary-${result.service_name.toLowerCase().replace(/\s+/g, "-")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
        Free Tools
      </h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Badge embed */}
        <div className="glass-card rounded-xl px-5 py-4 space-y-3">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
            </svg>
            <span className="text-xs font-semibold">AEO Badge</span>
          </div>
          {/* Live badge preview */}
          <div className="flex items-center justify-center py-2 bg-white/5 rounded-lg">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={badgeUrl} alt={`AEO Score: ${result.clarvia_score}`} height={20} />
          </div>
          {/* Style toggle */}
          <div className="flex gap-1">
            <button
              onClick={() => setBadgeStyle("flat")}
              className={`flex-1 text-[10px] py-1 rounded border transition-colors ${badgeStyle === "flat" ? "border-accent/50 text-accent" : "border-card-border text-muted hover:border-accent/30"}`}
            >
              Flat
            </button>
            <button
              onClick={() => setBadgeStyle("flat-square")}
              className={`flex-1 text-[10px] py-1 rounded border transition-colors ${badgeStyle === "flat-square" ? "border-accent/50 text-accent" : "border-card-border text-muted hover:border-accent/30"}`}
            >
              Square
            </button>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleCopyBadge("md")}
              className="flex-1 text-xs py-1.5 rounded-lg border border-card-border hover:border-accent/30 transition-colors"
            >
              {badgeCopied ? "Copied!" : "Markdown"}
            </button>
            <button
              onClick={() => handleCopyBadge("html")}
              className="flex-1 text-xs py-1.5 rounded-lg border border-card-border hover:border-accent/30 transition-colors"
            >
              HTML
            </button>
          </div>
        </div>

        {/* How to improve guide */}
        <Link
          href="/guide"
          className="glass-card rounded-xl px-5 py-4 space-y-3 hover:border-accent/30 transition-all group"
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
            </svg>
            <span className="text-xs font-semibold">AEO Guide</span>
          </div>
          <p className="text-xs text-muted">Learn how to improve your score with our step-by-step guide</p>
          <span className="text-xs text-accent group-hover:underline">Read guide →</span>
        </Link>

        {/* Mini report download */}
        <button
          onClick={handleDownloadMiniReport}
          className="glass-card rounded-xl px-5 py-4 space-y-3 text-left hover:border-accent/30 transition-all"
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            <span className="text-xs font-semibold">Quick Summary</span>
          </div>
          <p className="text-xs text-muted">Download score + top 3 recommendations as text</p>
          <span className="text-xs text-accent">Download .txt →</span>
        </button>

        {/* SARIF / CI/CD */}
        <div className="glass-card rounded-xl px-5 py-4 space-y-3">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l-5.09-2.71a2.5 2.5 0 01-.06-4.38l5.09-2.71a2.5 2.5 0 012.52.06l4.59 2.98a2.5 2.5 0 01-.06 4.28l-4.59 2.98a2.5 2.5 0 01-2.4-.5z" />
            </svg>
            <span className="text-xs font-semibold">CI/CD</span>
          </div>
          <p className="text-xs text-muted">SARIF export for GitHub Code Scanning + CI pipeline</p>
          <div className="flex gap-2">
            <a
              href={`${API_BASE}/api/scan/${result.scan_id}/sarif`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 text-center text-xs py-1.5 rounded-lg border border-card-border hover:border-accent/30 transition-colors"
            >
              SARIF ↓
            </a>
            <Link
              href="/docs#ci-cd"
              className="flex-1 text-center text-xs py-1.5 rounded-lg border border-card-border hover:border-accent/30 transition-colors text-accent"
            >
              Guide →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

// ----- Compare Section -----

interface PrebuiltScan {
  scan_id: string;
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

function CompareSection({ result }: { result: ScanResult }) {
  const [services, setServices] = useState<PrebuiltScan[]>([]);
  const [selected, setSelected] = useState<PrebuiltScan | null>(null);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/v1/services?sort=score_desc&limit=30&fields=full`)
      .then((r) => (r.ok ? r.json() : { services: [] }))
      .then((json) => {
        const raw = Array.isArray(json) ? json : (json.services || []);
        const items: PrebuiltScan[] = raw
          .filter((s: { scan_id: string }) => s.scan_id !== result.scan_id)
          .map((s: Record<string, unknown>) => ({
            scan_id: s.scan_id as string,
            service_name: (s.service_name as string) || (s.name as string) || "",
            clarvia_score: (s.clarvia_score as number) ?? 0,
            rating: (s.rating as string) ?? "Basic",
            dimensions: s.dimensions as PrebuiltScan["dimensions"],
          }));
        items.sort((a, b) => b.clarvia_score - a.clarvia_score);
        setServices(items);
      })
      .catch(console.warn);
  }, [result.scan_id]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = services.filter((s) =>
    s.service_name.toLowerCase().includes(search.toLowerCase())
  );

  const dimKeys = ["api_accessibility", "data_structuring", "agent_compatibility", "trust_signals"] as const;

  function deltaLabel(a: number, b: number): { text: string; color: string } {
    const diff = a - b;
    if (Math.abs(diff) <= 5) return { text: "Same", color: "text-score-yellow" };
    if (diff > 0) return { text: `+${diff}`, color: "text-score-green" };
    return { text: `${diff}`, color: "text-score-red" };
  }

  function barPct(score: number, max: number): number {
    return max > 0 ? (score / max) * 100 : 0;
  }

  const overallDiff = selected ? result.clarvia_score - selected.clarvia_score : 0;

  return (
    <div className="space-y-4">
      <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
        Compare your score
      </h2>

      {/* Service selector */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setOpen(!open)}
          className="w-full glass-card rounded-xl px-5 py-3.5 text-left flex items-center justify-between hover:border-accent/30 transition-colors"
        >
          <span className={`text-sm ${selected ? "text-foreground" : "text-muted"}`}>
            {selected ? selected.service_name : "Select a service to compare..."}
          </span>
          <svg
            className={`w-4 h-4 text-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {open && (
          <div className="absolute z-30 mt-2 w-full glass-card rounded-xl border border-card-border/60 overflow-hidden shadow-2xl">
            <div className="p-3 border-b border-card-border/30">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search services..."
                className="w-full bg-transparent text-sm text-foreground placeholder:text-muted/50 outline-none"
                autoFocus
              />
            </div>
            <div className="max-h-60 overflow-y-auto">
              {filtered.length === 0 && (
                <p className="px-4 py-3 text-xs text-muted">No services found</p>
              )}
              {filtered.map((s) => (
                <button
                  key={s.scan_id}
                  onClick={() => { setSelected(s); setOpen(false); setSearch(""); }}
                  className="w-full px-4 py-3 text-left hover:bg-card-border/20 transition-colors flex items-center justify-between"
                >
                  <span className="text-sm text-foreground">{s.service_name}</span>
                  <span className={`text-xs font-mono ${scoreTextClass(s.clarvia_score)}`}>
                    {s.clarvia_score}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Comparison card */}
      {selected && (
        <div className="glass-card rounded-xl overflow-hidden">
          {/* Header row */}
          <div className="grid grid-cols-[1fr_auto_1fr] items-center px-6 py-4 border-b border-card-border/30">
            <div className="text-center">
              <p className="text-xs text-muted mb-1">Your service</p>
              <p className="text-sm font-semibold truncate">{result.service_name}</p>
              <p className={`text-2xl font-mono font-bold mt-1 ${scoreTextClass(result.clarvia_score)}`}>
                {result.clarvia_score}
              </p>
            </div>
            <div className="px-4">
              <span className="text-xs text-muted font-mono">vs</span>
            </div>
            <div className="text-center">
              <p className="text-xs text-muted mb-1">Compared to</p>
              <p className="text-sm font-semibold truncate">{selected.service_name}</p>
              <p className={`text-2xl font-mono font-bold mt-1 ${scoreTextClass(selected.clarvia_score)}`}>
                {selected.clarvia_score}
              </p>
            </div>
          </div>

          {/* Dimension rows */}
          <div className="px-6 py-4 space-y-4">
            {dimKeys.map((dk) => {
              const myDim = result.dimensions[dk];
              const theirDim = selected.dimensions[dk];
              const meta = DIMENSION_META[dk];
              const d = deltaLabel(myDim.score, theirDim.score);

              return (
                <div key={dk} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-semibold ${meta?.iconColor || "text-foreground"}`}>
                      {meta?.label || dk}
                    </span>
                    <span className={`text-xs font-mono font-bold ${d.color}`}>
                      {d.text}
                    </span>
                  </div>
                  {/* Dual bars */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted w-16 truncate text-right">{result.service_name}</span>
                      <div className="flex-1 h-2 bg-card-border/30 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${scoreBgGradient(myDim.score, myDim.max)}`}
                          style={{ width: `${barPct(myDim.score, myDim.max)}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-muted w-8">{myDim.score}/{myDim.max}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted w-16 truncate text-right">{selected.service_name}</span>
                      <div className="flex-1 h-2 bg-card-border/30 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${scoreBgGradient(theirDim.score, theirDim.max)}`}
                          style={{ width: `${barPct(theirDim.score, theirDim.max)}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-muted w-8">{theirDim.score}/{theirDim.max}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Verdict */}
          <div className="px-6 py-4 border-t border-card-border/30 text-center">
            {overallDiff === 0 ? (
              <p className="text-sm text-score-yellow font-medium">
                Both services have the same Clarvia Score
              </p>
            ) : (
              <p className={`text-sm font-medium ${overallDiff > 0 ? "text-score-green" : "text-score-red"}`}>
                {result.service_name} scores{" "}
                <span className="font-mono font-bold">{Math.abs(overallDiff)}</span>{" "}
                point{Math.abs(overallDiff) !== 1 ? "s" : ""}{" "}
                {overallDiff > 0 ? "higher" : "lower"} than {selected.service_name}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ----- Badge Embed Snippet -----

function BadgeEmbed({ scanId, serviceName, score }: { scanId: string; serviceName: string; score: number }) {
  const [copied, setCopied] = useState<string | null>(null);
  const [style, setStyle] = useState<"flat" | "flat-square" | "for-the-badge">("flat");

  const badgeUrl = `https://clarvia.art/api/badge/${encodeURIComponent(scanId)}?style=${style}`;
  const reportUrl = `https://clarvia.art/tool/${encodeURIComponent(serviceName)}`;

  const snippets = {
    markdown: `[![Clarvia AEO Score](${badgeUrl})](${reportUrl})`,
    html: `<a href="${reportUrl}"><img src="${badgeUrl}" alt="Clarvia AEO Score" /></a>`,
    rst: `.. image:: ${badgeUrl}\n   :target: ${reportUrl}\n   :alt: Clarvia AEO Score`,
  };

  function handleCopy(key: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  }

  const badgeColor = score >= 80 ? "#4c1" : score >= 40 ? "#dfb317" : "#e05d44";

  return (
    <div className="card-glass rounded-2xl p-6 space-y-5">
      <div className="flex items-center gap-2">
        <svg className="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
        </svg>
        <h3 className="font-semibold text-base">Embed AEO Badge</h3>
      </div>
      <p className="text-sm text-muted">
        Show your AEO score on your README, docs, or website.
      </p>

      {/* Badge preview */}
      <div className="flex items-center justify-center py-4 bg-white/5 rounded-xl border border-card-border/30">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${API_BASE}/api/badge/${encodeURIComponent(scanId)}?style=${style}`}
          alt="AEO Score Badge"
          height={style === "for-the-badge" ? 28 : 20}
        />
      </div>

      {/* Style picker */}
      <div className="flex gap-2">
        {(["flat", "flat-square", "for-the-badge"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStyle(s)}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
              style === s
                ? "border-accent bg-accent/10 text-accent"
                : "border-card-border/30 text-muted hover:text-foreground hover:border-card-border/60"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Snippet tabs */}
      <div className="space-y-3">
        {(Object.entries(snippets) as [string, string][]).map(([key, snippet]) => (
          <div key={key} className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted uppercase tracking-wider">
                {key === "rst" ? "reStructuredText" : key}
              </span>
              <button
                onClick={() => handleCopy(key, snippet)}
                className="text-xs text-accent hover:text-accent/80 transition-colors flex items-center gap-1"
              >
                {copied === key ? (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    Copied
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                  </>
                )}
              </button>
            </div>
            <pre className="bg-black/30 rounded-lg px-3 py-2 text-xs text-muted font-mono overflow-x-auto whitespace-pre-wrap break-all border border-card-border/20">
              {snippet}
            </pre>
          </div>
        ))}
      </div>

      <p className="text-xs text-muted/60">
        Badge auto-updates when the score changes. JSON endpoint available at{" "}
        <code className="text-accent/80">/api/badge/{serviceName}/json</code>
      </p>
    </div>
  );
}

// ----- Full Scan Result View (with history + paywall) -----

function ScanResultView({
  result,
  appeared,
  handleGetReport,
  checkoutLoading,
}: {
  result: ScanResult;
  appeared: boolean;
  handleGetReport: () => void;
  checkoutLoading: boolean;
}) {
  const { previousScore, history } = useScanHistory(result.url, result.clarvia_score);
  const percentile = usePercentile(result.url);
  const isVerified = result.clarvia_score >= 70;

  return (
    <div
      className={`space-y-10 transition-all duration-700 ${
        appeared ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
      }`}
    >
      {/* First-visit guide banner */}
      <div className="glass-card rounded-xl px-5 py-4 border-accent/20 bg-accent/5">
        <p className="text-xs text-muted leading-relaxed text-center">
          <span className="text-accent font-semibold">What is this report?</span>{" "}
          This measures how easily AI agents can discover, connect to, and use this tool.
          A higher score means agents can integrate with less friction.
        </p>
      </div>

      {/* Service header */}
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold">{result.service_name}</h1>
        <p className="text-sm text-muted font-mono">{result.url}</p>
        <div className="flex justify-center pt-1">
          <ShareButtons result={result} />
        </div>
      </div>

      {/* Score + Grade */}
      <div className="flex flex-col items-center space-y-5">
        <ScoreGauge score={result.clarvia_score} />
        <div className="flex items-center gap-3 flex-wrap justify-center">
          <span
            className={`inline-block px-4 py-1.5 rounded-xl border text-xs font-mono uppercase tracking-wider ${gradeBadgeClass(result.rating)}`}
          >
            {result.rating}
          </span>
          {result.agent_grade && (() => {
            const gm = agentGradeMeta(result.agent_grade);
            return (
              <span className="group relative">
                <span className={`inline-block px-4 py-1.5 rounded-xl border text-xs font-mono tracking-wider cursor-help ${gm.colorClass}`}>
                  {gm.label}
                </span>
                {gm.description && (
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-2.5 rounded-xl bg-card-bg border border-card-border text-xs text-muted leading-relaxed opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-lg text-center">
                    {gm.description}
                  </span>
                )}
              </span>
            );
          })()}
          {isVerified && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-mono bg-score-green/10 text-score-green border-score-green/20">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
              </svg>
              Agent Verified
            </span>
          )}
          {percentile && (
            <PercentileBadge
              percentile={percentile.percentile}
              rank={percentile.rank}
              total={percentile.total}
            />
          )}
          {(previousScore !== null || history.length >= 2) && (
            <ScoreDelta
              previous={previousScore ?? result.clarvia_score}
              current={result.clarvia_score}
              history={history}
            />
          )}
        </div>
        <p className={`text-sm text-center max-w-lg mx-auto pt-2 leading-relaxed ${scoreTextClass(result.clarvia_score)}`}>
          {scoreInterpretation(result.clarvia_score)}
        </p>
      </div>

      {/* Dimensions */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Dimensions
          </h2>
          <p className="text-xs text-muted/60 mt-1">
            Your score is broken down into 4 areas. Hover [?] for explanations.
          </p>
        </div>
        {result.dimensions && Object.entries(result.dimensions).map(([key, dim]) => (
          <DimensionBar key={key} dimKey={key} dimension={dim} />
        ))}
      </div>

      {/* Onchain bonus — only show if applicable */}
      {result.onchain_bonus?.applicable && (
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Onchain Bonus
          </h2>
          <div className="glass-card rounded-xl px-6 py-5">
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
          </div>
        </div>
      )}

      {/* Agent Accessibility Probe (Data Moat C) */}
      <AgentProbeSection url={result.url} />

      {/* Improvement Playbook */}
      <PlaybookSection scanId={result.scan_id} />

      {/* History & Trends */}
      {result.dimensions && <HistorySection url={result.url} currentScore={result.clarvia_score} currentDimensions={result.dimensions} />}

      {/* Recommendations — show only top 3 free */}
      {result.top_recommendations.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Top Recommendations
          </h2>
          <div className="space-y-3">
            {result.top_recommendations.slice(0, 3).map((rec, i) => (
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
            {result.top_recommendations.length > 3 && (
              <div className="rounded-xl px-6 py-4 border border-card-border/30 bg-card-bg/50 text-center">
                <p className="text-xs text-muted">
                  +{result.top_recommendations.length - 3} more recommendations in the full report
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Share + Actions */}
      <div className="space-y-4">
        <h2 className="text-xs font-mono text-accent uppercase tracking-widest">Share</h2>
        <ShareButtons result={result} />
      </div>

      {/* Free Actions */}
      <FreeActions result={result} />

      {/* Compare */}
      <CompareSection result={result} />

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
              <li>All sub-factors with detailed evidence (unblurred)</li>
              <li>15 recommendations with prioritized implementation roadmap</li>
              <li>Competitive benchmark vs 44 scanned services</li>
              <li>Stack-specific code examples for top improvements</li>
              <li>Radar chart + branded PDF report</li>
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
        <p className="text-center text-xs text-muted">
          Or{" "}
          <Link href="/pricing" className="text-accent hover:underline">
            subscribe to Pro for unlimited reports — $29/mo
          </Link>
        </p>
      </div>

      {/* Get Badge */}
      <BadgeEmbed scanId={result.scan_id} serviceName={result.service_name} score={result.clarvia_score} />

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
    if (result) {
      document.title = `${result.service_name} — Clarvia Score ${result.clarvia_score}`;
    }
  }, [result]);

  useEffect(() => {
    if (!scanId) return;

    async function fetchWithRetry(url: string, retries = 2, delay = 1500): Promise<Response> {
      for (let attempt = 0; attempt <= retries; attempt++) {
        try {
          const res = await fetch(url);
          if (res.ok || res.status === 404) return res;
          if (attempt < retries) {
            await new Promise((r) => setTimeout(r, delay));
            continue;
          }
          return res;
        } catch (err) {
          if (attempt < retries) {
            await new Promise((r) => setTimeout(r, delay));
            continue;
          }
          throw err;
        }
      }
      throw new Error("Max retries exceeded");
    }

    async function fetchResult() {
      try {
        const res = await fetchWithRetry(`${API_BASE}/api/scan/${scanId}`);
        if (res.ok) {
          const data = await res.json();
          setResult(data);
          requestAnimationFrame(() => setAppeared(true));
          return;
        }

        // Fallback 1: Try /v1/services/{scan_id} (lightweight, for collected tools)
        try {
          const svcRes = await fetch(`${API_BASE}/v1/services/${scanId}`);
          if (svcRes.ok) {
            const svc = await svcRes.json();
            // Normalize collected tool data to match ScanResult shape
            if (!svc.dimensions && svc.scoring) svc.dimensions = svc.scoring;
            if (!svc.service_name && svc.name) svc.service_name = svc.name;
            if (!svc.clarvia_score && svc.score) svc.clarvia_score = svc.score;
            if (!svc.top_recommendations) svc.top_recommendations = [];
            if (!svc.scan_duration_ms) svc.scan_duration_ms = 0;
            if (!svc.onchain_bonus) svc.onchain_bonus = { score: 0, max: 10, applicable: false, sub_factors: {} };
            setResult(svc);
            requestAnimationFrame(() => setAppeared(true));
            return;
          }
        } catch { /* continue to next fallback */ }

        // No more fallbacks — scan not found
        throw new Error(`Scan not found (${scanId})`);
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
      <Nav />

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12">
        {loading && !error && <ScanningView />}
        {/* CSS-only fallback shown immediately before JS hydration */}
        <noscript>
          <div className="flex flex-col items-center justify-center min-h-[60vh]">
            <p className="text-muted text-sm">Loading scan results...</p>
          </div>
        </noscript>

        {error && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-score-red/10 flex items-center justify-center mb-2">
              <svg className="w-8 h-8 text-score-red" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <p className="text-score-red font-mono text-sm">{error}</p>
            <div className="flex gap-4">
              <button
                onClick={() => { setError(""); setLoading(true); window.location.reload(); }}
                className="text-accent hover:text-accent-hover text-sm transition-colors font-medium"
              >
                Try again
              </button>
              <Link
                href="/"
                className="text-muted hover:text-foreground text-sm transition-colors"
              >
                Back to scanner
              </Link>
            </div>
          </div>
        )}

        {result && <ScanResultView result={result} appeared={appeared} handleGetReport={handleGetReport} checkoutLoading={checkoutLoading} />}
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
            <span>Clarvia — Discovery & Trust standard for the agent economy</span>
          </div>
          <div className="flex items-center gap-4">
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
