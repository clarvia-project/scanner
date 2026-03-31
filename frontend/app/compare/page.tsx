"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

// ─── Legacy DB-mode types ────────────────────────────────────────────────────

interface ComparedTool {
  name: string;
  url: string;
  description?: string;
  category: string;
  service_type: string;
  clarvia_score: number;
  rating: string;
  dimensions: Record<string, number>;
  scan_id: string;
  connection_info?: Record<string, unknown>;
  last_scanned?: string;
}

// ─── New URL-compare types ────────────────────────────────────────────────────

interface CompareService {
  url: string;
  name: string;
  score: number | null;
  rating: string;
  dimensions: Record<string, { score: number; max: number }>;
  error?: string;
}

interface CompareResult {
  services: CompareService[];
  winner: string | null;
  winner_score_diff: number;
  dimension_winners: Record<string, string>;
  summary: string;
}

// ─── Shared helpers ───────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  mcp_server: { label: "MCP Server", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  api: { label: "API", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  cli_tool: { label: "CLI Tool", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  skill: { label: "Skill", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  general: { label: "General", color: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
};

const DIMENSION_LABELS: Record<string, string> = {
  documentation: "Documentation",
  authentication: "Authentication",
  error_handling: "Error Handling",
  versioning: "Versioning",
  rate_limiting: "Rate Limiting",
  api_accessibility: "API Accessibility",
  data_structuring: "Data Structuring",
  agent_compatibility: "Agent Compat.",
  trust_signals: "Trust Signals",
};

function scoreColor(score: number | null) {
  if (score === null) return "text-muted";
  if (score >= 70) return "text-score-green";
  if (score >= 50) return "text-score-yellow";
  return "text-score-red";
}

function scoreBg(score: number | null) {
  if (score === null) return "bg-card-border/10 border-card-border/20";
  if (score >= 70) return "bg-score-green/10 border-score-green/20";
  if (score >= 50) return "bg-score-yellow/10 border-score-yellow/20";
  return "bg-score-red/10 border-score-red/20";
}

function scoreRating(score: number | null): string {
  if (score === null) return "Unknown";
  if (score >= 80) return "Strong";
  if (score >= 60) return "Moderate";
  if (score >= 40) return "Weak";
  return "Poor";
}

function barColor(pct: number) {
  if (pct >= 70) return "#22c55e";
  if (pct >= 40) return "#eab308";
  return "#ef4444";
}

function getFaviconUrl(url: string): string | null {
  if (!url) return null;
  try {
    const domain = new URL(url.startsWith("http") ? url : `https://${url}`).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
  } catch {
    return null;
  }
}

function ServiceIcon({ url, name }: { url: string; name: string }) {
  const [error, setError] = useState(false);
  const favicon = getFaviconUrl(url);

  if (!favicon || error) {
    return (
      <div className="w-10 h-10 rounded-lg bg-card-border/40 flex items-center justify-center flex-shrink-0">
        <span className="text-sm font-bold text-muted/70">
          {(name || "?").charAt(0).toUpperCase()}
        </span>
      </div>
    );
  }

  return (
    <img
      src={favicon}
      alt=""
      width={40}
      height={40}
      className="w-10 h-10 rounded-lg bg-card-border/30 p-1.5 flex-shrink-0 object-contain"
      onError={() => setError(true)}
    />
  );
}

// ─── Legacy helpers ───────────────────────────────────────────────────────────

function getInstallHint(tool: ComparedTool): { label: string; command: string } | null {
  const ci = tool.connection_info || {};
  if (tool.service_type === "mcp_server") {
    const install = ci.install as string | undefined;
    const cmd = install
      ? `npx -y ${install.replace("npm install ", "")}`
      : `claude mcp add ${tool.name.toLowerCase().replace(/[^a-z0-9-]/g, "-")}`;
    return { label: "Add to Claude Code", command: cmd };
  }
  if (tool.service_type === "cli_tool") {
    return { label: "Install CLI", command: (ci.install as string) || `npm install ${tool.name}` };
  }
  if (tool.service_type === "api") {
    return { label: "API Endpoint", command: (ci.base_url as string) || tool.url };
  }
  return null;
}

function ShareButtons({ label, href }: { label: string; href: string }) {
  const text = `${label} — AEO Score Comparison\n\nCompare at`;

  const copyLink = () => {
    navigator.clipboard.writeText(href);
  };

  return (
    <div className="flex items-center gap-2">
      <a
        href={`https://x.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(href)}`}
        target="_blank"
        rel="noopener noreferrer"
        className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:border-accent/30 transition-all flex items-center gap-1.5"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
        Post
      </a>
      <a
        href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(href)}`}
        target="_blank"
        rel="noopener noreferrer"
        className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:border-accent/30 transition-all flex items-center gap-1.5"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
        </svg>
        Share
      </a>
      <button
        onClick={copyLink}
        className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:border-accent/30 transition-all flex items-center gap-1.5 cursor-pointer"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        Copy
      </button>
    </div>
  );
}

// ─── New URL Compare Table ────────────────────────────────────────────────────

function CompareTable({ result }: { result: CompareResult }) {
  const { services, winner, winner_score_diff, dimension_winners, summary } = result;

  const allDims = Array.from(
    new Set(services.flatMap((s) => Object.keys(s.dimensions)))
  );

  const shareLabel = services.map((s) => s.name || s.url).join(" vs ");
  const shareHref = typeof window !== "undefined" ? window.location.href : "";

  return (
    <div className="space-y-6">
      {/* Winner banner */}
      <div className="glass-card rounded-2xl p-8">
        {/* Header row: service vs service */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 mb-6">
          {services.map((svc, idx) => {
            const isWinner = winner === svc.url || winner === svc.name;
            return (
              <div
                key={svc.url}
                className={`flex flex-col items-center gap-2 ${idx === 1 ? "col-start-3" : ""}`}
              >
                <div className="flex items-center gap-2">
                  <ServiceIcon url={svc.url} name={svc.name || svc.url} />
                  <div className="text-left">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-semibold text-sm">
                        {svc.name || svc.url}
                      </span>
                      {isWinner && (
                        <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg px-2 py-0.5 text-xs font-mono">
                          WINNER
                        </span>
                      )}
                    </div>
                    <div className={`text-xs font-mono mt-0.5 ${scoreColor(svc.score)}`}>
                      {svc.score !== null ? svc.score : "—"} · {svc.score !== null ? scoreRating(svc.score) : svc.rating || "N/A"}
                    </div>
                  </div>
                </div>
                {/* Score pill */}
                <div className={`text-center py-2 px-4 rounded-xl border ${scoreBg(svc.score)} min-w-[80px]`}>
                  <div className={`text-2xl font-bold font-mono ${scoreColor(svc.score)}`}>
                    {svc.score !== null ? svc.score : "—"}
                  </div>
                  <div className="text-[10px] text-muted mt-0.5">{svc.rating || scoreRating(svc.score)}</div>
                </div>
              </div>
            );
          })}

          {/* VS divider */}
          <div className="col-start-2 flex flex-col items-center gap-1">
            <span className="text-xs font-mono text-muted/40 uppercase tracking-widest">vs</span>
          </div>
        </div>

        {/* Dimension table */}
        {allDims.length > 0 && (
          <div className="rounded-xl overflow-hidden border border-card-border/40">
            {/* Table header */}
            <div className="grid grid-cols-3 bg-card-border/10 px-4 py-2.5 text-[10px] font-mono text-muted/60 uppercase tracking-wider">
              <div>Dimension</div>
              <div className="text-center">{services[0]?.name || services[0]?.url}</div>
              <div className="text-center">{services[1]?.name || services[1]?.url}</div>
            </div>

            {/* Table rows */}
            <div className="divide-y divide-card-border/30">
              {allDims.map((dim) => {
                const a = services[0]?.dimensions[dim];
                const b = services[1]?.dimensions[dim];
                const dimWinner = dimension_winners?.[dim];
                const aWins = dimWinner === services[0]?.url || dimWinner === services[0]?.name;
                const bWins = dimWinner === services[1]?.url || dimWinner === services[1]?.name;

                return (
                  <div key={dim} className="grid grid-cols-3 px-4 py-3 items-center hover:bg-card-border/5 transition-colors">
                    <div className="text-xs text-muted capitalize">
                      {DIMENSION_LABELS[dim] || dim.replace(/_/g, " ")}
                    </div>

                    {/* Service A score */}
                    <div className="text-center">
                      {a !== undefined ? (
                        <span className={`text-xs font-mono font-medium inline-flex items-center gap-1 ${aWins ? "text-emerald-400" : "text-foreground/70"}`}>
                          {a.score}/{a.max}
                          {aWins && <span className="text-emerald-400">✓</span>}
                        </span>
                      ) : (
                        <span className="text-xs text-muted/30">—</span>
                      )}
                    </div>

                    {/* Service B score */}
                    <div className="text-center">
                      {b !== undefined ? (
                        <span className={`text-xs font-mono font-medium inline-flex items-center gap-1 ${bWins ? "text-emerald-400" : "text-foreground/70"}`}>
                          {b.score}/{b.max}
                          {bWins && <span className="text-emerald-400">✓</span>}
                        </span>
                      ) : (
                        <span className="text-xs text-muted/30">—</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div className="mt-4 px-4 py-3 rounded-xl bg-card-border/10 border border-card-border/20">
            <p className="text-xs text-muted leading-relaxed">
              <span className="text-foreground/70 font-medium">Summary: </span>
              {summary}
              {winner_score_diff > 0 && (
                <span className="text-muted/60"> ({winner_score_diff} point{winner_score_diff !== 1 ? "s" : ""} ahead)</span>
              )}
            </p>
          </div>
        )}
      </div>

      {/* Share row */}
      <div className="flex flex-col items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted font-mono">Share comparison:</span>
          <ShareButtons label={shareLabel} href={shareHref} />
        </div>
        <Link href="/tools" className="text-sm text-muted hover:text-accent transition-colors">
          &larr; Back to Tool Directory
        </Link>
      </div>
    </div>
  );
}

// ─── Legacy DB compare cards (unchanged visual) ───────────────────────────────

function LegacyCompareCards({ tools }: { tools: ComparedTool[] }) {
  const allDimensions = Array.from(
    new Set(tools.flatMap((t) => Object.keys(t.dimensions)))
  );

  const shareLabel = tools.map((t) => t.name).join(" vs ");
  const shareHref = typeof window !== "undefined" ? window.location.href : "";

  return (
    <>
      <div
        className={`grid gap-4 ${
          tools.length === 1
            ? "grid-cols-1 max-w-md"
            : tools.length === 2
            ? "grid-cols-1 md:grid-cols-2"
            : tools.length === 3
            ? "grid-cols-1 md:grid-cols-3"
            : "grid-cols-1 md:grid-cols-2 lg:grid-cols-4"
        }`}
      >
        {tools.map((tool) => {
          const typeInfo = TYPE_LABELS[tool.service_type] || TYPE_LABELS.general;
          const hint = getInstallHint(tool);
          return (
            <div key={tool.scan_id} className="glass-card rounded-xl p-5 flex flex-col">
              <div className="flex items-center gap-3 mb-4">
                <ServiceIcon url={tool.url} name={tool.name} />
                <div className="min-w-0 flex-1">
                  <Link
                    href={tool.scan_id.startsWith("tool_") ? `/tool/${tool.scan_id}` : `/scan/${tool.scan_id}`}
                    className="text-sm font-semibold truncate block hover:text-accent transition-colors"
                  >
                    {tool.name}
                  </Link>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${typeInfo.color}`}>
                      {typeInfo.label}
                    </span>
                    <span className="text-[10px] text-muted/50 font-mono">{tool.category}</span>
                  </div>
                </div>
              </div>

              <div className={`text-center py-3 rounded-xl border mb-4 ${scoreBg(tool.clarvia_score)}`}>
                <div className={`text-2xl font-bold font-mono ${scoreColor(tool.clarvia_score)}`}>
                  {tool.clarvia_score}
                </div>
                <div className="text-[10px] text-muted mt-0.5">{tool.rating}</div>
              </div>

              <div className="space-y-2.5 mb-4 flex-1">
                {allDimensions.map((dim) => {
                  const val = tool.dimensions[dim] ?? 0;
                  const maxVal = 25;
                  const pct = (val / maxVal) * 100;
                  return (
                    <div key={dim}>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-[10px] text-muted capitalize">
                          {DIMENSION_LABELS[dim] || dim.replace(/_/g, " ")}
                        </span>
                        <span className="text-[10px] font-mono font-medium">
                          {val}/{maxVal}
                        </span>
                      </div>
                      <div className="h-1.5 bg-card-border/30 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{ width: `${pct}%`, background: barColor(pct) }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {tool.url && (
                <a
                  href={tool.url.startsWith("http") ? tool.url : `https://${tool.url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-accent hover:underline font-mono truncate block mb-3"
                >
                  {tool.url.replace(/^https?:\/\//, "").slice(0, 40)}
                </a>
              )}

              {hint && (
                <div className="mt-auto">
                  <div className="text-[10px] text-muted/50 font-mono mb-1">{hint.label}</div>
                  <code className="block bg-black/30 px-2 py-1.5 rounded-lg text-[10px] font-mono text-accent/80 overflow-x-auto">
                    {hint.command}
                  </code>
                </div>
              )}
            </div>
          );
        })}

        {tools.length < 4 && (
          <Link
            href="/tools"
            className="glass-subtle rounded-xl p-5 flex flex-col items-center justify-center gap-2 border-dashed border-card-border/50 hover:border-accent/30 transition-all min-h-[300px]"
          >
            <div className="text-2xl text-muted/30">+</div>
            <span className="text-xs text-muted/50">Add tool</span>
          </Link>
        )}
      </div>

      <div className="mt-8 flex flex-col items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted font-mono">Share comparison:</span>
          <ShareButtons label={shareLabel} href={shareHref} />
        </div>
        <Link href="/tools" className="text-sm text-muted hover:text-accent transition-colors">
          &larr; Back to Tool Directory
        </Link>
      </div>
    </>
  );
}

// ─── Input form ───────────────────────────────────────────────────────────────

function InputForm({
  inputA,
  inputB,
  setInputA,
  setInputB,
  onSubmit,
}: {
  inputA: string;
  inputB: string;
  setInputA: (v: string) => void;
  setInputB: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}) {
  return (
    <div className="glass-card rounded-xl p-12 text-center space-y-6 max-w-lg mx-auto">
      <div className="text-4xl mb-2">⇄</div>
      <h2 className="text-lg font-semibold">Compare two services</h2>
      <form onSubmit={onSubmit} className="space-y-3 text-left">
        <input
          type="text"
          value={inputA}
          onChange={(e) => setInputA(e.target.value)}
          placeholder="Service A (e.g. stripe.com)"
          className="w-full bg-card-bg/80 border border-card-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-accent/50 font-mono text-sm"
        />
        <input
          type="text"
          value={inputB}
          onChange={(e) => setInputB(e.target.value)}
          placeholder="Service B (e.g. plaid.com)"
          className="w-full bg-card-bg/80 border border-card-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-accent/50 font-mono text-sm"
        />
        <button
          type="submit"
          disabled={!inputA.trim() || !inputB.trim()}
          className="w-full btn-gradient text-white px-4 py-3 rounded-xl text-sm font-medium disabled:opacity-40"
        >
          Compare
        </button>
      </form>
      <p className="text-muted text-xs">
        Or{" "}
        <Link href="/tools" className="text-accent hover:underline">
          browse tools
        </Link>{" "}
        and click Compare on any tool page.
      </p>
    </div>
  );
}

// ─── Page shell ───────────────────────────────────────────────────────────────

export default function ComparePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <CompareContent />
    </Suspense>
  );
}

// ─── Main content ─────────────────────────────────────────────────────────────

type Mode = "idle" | "loading" | "url-result" | "legacy-result" | "error";

function CompareContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Query-param sources
  const paramUrls = searchParams.get("urls") || "";          // e.g. "stripe.com,plaid.com"
  const paramA = searchParams.get("a") || "";                // e.g. "stripe.com"
  const paramB = searchParams.get("b") || "";                // e.g. "plaid.com"
  const paramIds = searchParams.get("ids") || "";            // legacy DB ids
  const paramNames = searchParams.get("names") || "";        // legacy DB names

  // Form state
  const [inputA, setInputA] = useState("");
  const [inputB, setInputB] = useState("");

  // Result state
  const [mode, setMode] = useState<Mode>("idle");
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [legacyTools, setLegacyTools] = useState<ComparedTool[]>([]);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    // Determine which mode to use
    const urlPair = (() => {
      if (paramUrls) {
        const parts = paramUrls.split(",").map((s) => s.trim()).filter(Boolean);
        if (parts.length >= 2) return [parts[0], parts[1]] as [string, string];
      }
      if (paramA && paramB) return [paramA, paramB] as [string, string];
      return null;
    })();

    const legacyQuery = paramIds
      ? `ids=${encodeURIComponent(paramIds)}`
      : paramNames
      ? `names=${encodeURIComponent(paramNames)}`
      : "";

    if (urlPair) {
      // New URL-scan mode
      setMode("loading");
      setCompareResult(null);
      setLegacyTools([]);
      setErrorMsg("");

      const [u1, u2] = urlPair;
      fetch(`${API_BASE}/api/v1/compare?urls=${encodeURIComponent(u1)},${encodeURIComponent(u2)}`)
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json() as Promise<CompareResult>;
        })
        .then((data) => {
          setCompareResult(data);
          setMode("url-result");
        })
        .catch((err: unknown) => {
          const msg = err instanceof Error ? err.message : "Unknown error";
          setErrorMsg(`Failed to compare: ${msg}`);
          setMode("error");
        });
    } else if (legacyQuery) {
      // Legacy DB mode
      setMode("loading");
      setCompareResult(null);
      setLegacyTools([]);
      setErrorMsg("");

      fetch(`${API_BASE}/v1/compare?${legacyQuery}`)
        .then((r) => r.json())
        .then((data) => {
          setLegacyTools((data.services as ComparedTool[]) || []);
          setMode("legacy-result");
        })
        .catch(() => {
          setLegacyTools([]);
          setMode("idle");
        });
    } else {
      setMode("idle");
    }
  }, [paramUrls, paramA, paramB, paramIds, paramNames]);

  function handleCompareSubmit(e: React.FormEvent) {
    e.preventDefault();
    const a = inputA.trim();
    const b = inputB.trim();
    if (!a || !b) return;
    router.push(`/compare?urls=${encodeURIComponent(`${a},${b}`)}`);
  }

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
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">Leaderboard</Link>
              <Link href="/guide" className="text-sm text-muted hover:text-foreground transition-colors">Guide</Link>
              <Link href="/register" className="text-sm text-muted hover:text-foreground transition-colors">Register</Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">Docs</Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-muted/60 font-mono mb-6">
          <Link href="/tools" className="hover:text-accent">Tools</Link>
          <span>/</span>
          <span className="text-muted">Compare</span>
        </div>

        <div className="mb-8 space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Compare Tools</h1>
          <p className="text-muted">Side-by-side AEO score comparison.</p>
        </div>

        {mode === "loading" && (
          <div className="glass-card rounded-2xl p-16 flex flex-col items-center gap-4">
            <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted font-mono">Scanning and comparing...</p>
          </div>
        )}

        {mode === "error" && (
          <div className="glass-card rounded-2xl p-12 text-center space-y-4 max-w-lg mx-auto">
            <p className="text-sm text-score-red font-mono">{errorMsg}</p>
            <button
              onClick={() => {
                setMode("idle");
                router.push("/compare");
              }}
              className="text-sm text-accent hover:underline"
            >
              Try again
            </button>
          </div>
        )}

        {mode === "idle" && (
          <InputForm
            inputA={inputA}
            inputB={inputB}
            setInputA={setInputA}
            setInputB={setInputB}
            onSubmit={handleCompareSubmit}
          />
        )}

        {mode === "url-result" && compareResult && (
          <CompareTable result={compareResult} />
        )}

        {mode === "legacy-result" && (
          legacyTools.length === 0 ? (
            <InputForm
              inputA={inputA}
              inputB={inputB}
              setInputA={setInputA}
              setInputB={setInputB}
              onSubmit={handleCompareSubmit}
            />
          ) : (
            <LegacyCompareCards tools={legacyTools} />
          )
        )}
      </main>

      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia — The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}
