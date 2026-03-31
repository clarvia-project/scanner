"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

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
};

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function scoreBg(score: number) {
  if (score >= 70) return "bg-score-green/10 border-score-green/20";
  if (score >= 40) return "bg-score-yellow/10 border-score-yellow/20";
  return "bg-score-red/10 border-score-red/20";
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

function ShareButtons({ tools }: { tools: ComparedTool[] }) {
  const names = tools.map((t) => t.name).join(" vs ");
  const scores = tools.map((t) => `${t.name}: ${t.clarvia_score}`).join(", ");
  const url = typeof window !== "undefined" ? window.location.href : "";
  const text = `${names} — AEO Score Comparison\n${scores}\n\nCompare at`;

  const copyLink = () => {
    navigator.clipboard.writeText(url);
  };

  return (
    <div className="flex items-center gap-2">
      {/* X/Twitter */}
      <a
        href={`https://x.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`}
        target="_blank"
        rel="noopener noreferrer"
        className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:border-accent/30 transition-all flex items-center gap-1.5"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
        Post
      </a>
      {/* LinkedIn */}
      <a
        href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`}
        target="_blank"
        rel="noopener noreferrer"
        className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:border-accent/30 transition-all flex items-center gap-1.5"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
        </svg>
        Share
      </a>
      {/* Copy Link */}
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

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" /></div>}>
      <CompareContent />
    </Suspense>
  );
}

function CompareContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const ids = searchParams.get("ids") || "";
  const names = searchParams.get("names") || "";
  const [tools, setTools] = useState<ComparedTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [inputA, setInputA] = useState("");
  const [inputB, setInputB] = useState("");

  useEffect(() => {
    const query = ids ? `ids=${encodeURIComponent(ids)}` : names ? `names=${encodeURIComponent(names)}` : "";
    if (!query) {
      setLoading(false);
      return;
    }
    fetch(`${API_BASE}/v1/compare?${query}`)
      .then((r) => r.json())
      .then((data) => setTools(data.services || []))
      .catch(() => setTools([]))
      .finally(() => setLoading(false));
  }, [ids, names]);

  function handleCompareSubmit(e: React.FormEvent) {
    e.preventDefault();
    const a = inputA.trim();
    const b = inputB.trim();
    if (!a || !b) return;
    router.push(`/compare?names=${encodeURIComponent(`${a},${b}`)}`);
  }

  // Collect all dimension keys across tools
  const allDimensions = Array.from(
    new Set(tools.flatMap((t) => Object.keys(t.dimensions)))
  );

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
          <p className="text-muted">
            Side-by-side comparison of up to 4 agent tools.
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-card rounded-xl p-6 h-80 animate-pulse" />
            ))}
          </div>
        ) : tools.length === 0 ? (
          <div className="glass-card rounded-xl p-12 text-center space-y-6 max-w-lg mx-auto">
            <div className="text-4xl mb-2">⇄</div>
            <h2 className="text-lg font-semibold">Compare two tools</h2>
            <form onSubmit={handleCompareSubmit} className="space-y-3 text-left">
              <input
                type="text"
                value={inputA}
                onChange={(e) => setInputA(e.target.value)}
                placeholder="Tool A (e.g. stripe.com)"
                className="w-full bg-card-bg/80 border border-card-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-accent/50 font-mono text-sm"
              />
              <input
                type="text"
                value={inputB}
                onChange={(e) => setInputB(e.target.value)}
                placeholder="Tool B (e.g. replicate.com)"
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
              <Link href="/tools" className="text-accent hover:underline">browse tools</Link>
              {" "}and click Compare on any tool page.
            </p>
          </div>
        ) : (
          <>
            {/* Tool cards - responsive grid */}
            <div className={`grid gap-4 ${
              tools.length === 1 ? "grid-cols-1 max-w-md" :
              tools.length === 2 ? "grid-cols-1 md:grid-cols-2" :
              tools.length === 3 ? "grid-cols-1 md:grid-cols-3" :
              "grid-cols-1 md:grid-cols-2 lg:grid-cols-4"
            }`}>
              {tools.map((tool) => {
                const typeInfo = TYPE_LABELS[tool.service_type] || TYPE_LABELS.general;
                const hint = getInstallHint(tool);
                return (
                  <div key={tool.scan_id} className="glass-card rounded-xl p-5 flex flex-col">
                    {/* Header */}
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

                    {/* Score */}
                    <div className={`text-center py-3 rounded-xl border mb-4 ${scoreBg(tool.clarvia_score)}`}>
                      <div className={`text-2xl font-bold font-mono ${scoreColor(tool.clarvia_score)}`}>
                        {tool.clarvia_score}
                      </div>
                      <div className="text-[10px] text-muted mt-0.5">{tool.rating}</div>
                    </div>

                    {/* Dimensions */}
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

                    {/* URL */}
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

                    {/* Install hint */}
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

              {/* Add more slot */}
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

            {/* Share buttons */}
            <div className="mt-8 flex flex-col items-center gap-4">
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted font-mono">Share comparison:</span>
                <ShareButtons tools={tools} />
              </div>
              <Link href="/tools" className="text-sm text-muted hover:text-accent transition-colors">
                &larr; Back to Tool Directory
              </Link>
            </div>
          </>
        )}
      </main>

      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia — The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}
