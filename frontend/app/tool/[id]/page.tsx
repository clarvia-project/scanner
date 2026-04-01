"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE, stripHtml } from "@/lib/api";

function BadgeEmbed({ toolId }: { toolId: string }) {
  const [copied, setCopied] = useState<string | null>(null);
  const badgeUrl = `https://clarvia.art/api/badge/${toolId}`;
  const profileUrl = `https://clarvia.art/tool/${toolId}`;
  const markdown = `[![Clarvia Score](${badgeUrl})](${profileUrl})`;
  const html = `<a href="${profileUrl}"><img src="${badgeUrl}" alt="Clarvia Score" /></a>`;

  const copy = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="glass-card rounded-xl p-6">
      <h2 className="text-sm font-semibold mb-3">Embed AEO Badge</h2>
      <p className="text-xs text-muted/60 mb-4">Add this badge to your README to show your Clarvia Score.</p>
      <div className="mb-4 flex items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={badgeUrl} alt="Clarvia Score badge preview" height={20} />
        <span className="text-xs text-muted/50">live badge</span>
      </div>
      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-muted/50 font-mono uppercase">Markdown</span>
            <button onClick={() => copy(markdown, "md")} className="text-[10px] text-muted/50 hover:text-accent transition-colors cursor-pointer">
              {copied === "md" ? "Copied!" : "Copy"}
            </button>
          </div>
          <div className="text-xs font-mono bg-card-border/20 rounded-lg px-3 py-2 break-all">{markdown}</div>
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-muted/50 font-mono uppercase">HTML</span>
            <button onClick={() => copy(html, "html")} className="text-[10px] text-muted/50 hover:text-accent transition-colors cursor-pointer">
              {copied === "html" ? "Copied!" : "Copy"}
            </button>
          </div>
          <div className="text-xs font-mono bg-card-border/20 rounded-lg px-3 py-2 break-all">{html}</div>
        </div>
      </div>
    </div>
  );
}

function ShareButtons({ url, title }: { url: string; title: string }) {
  const [copied, setCopied] = useState(false);

  const shareTwitter = () => {
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`, '_blank');
  };

  const shareLinkedIn = () => {
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`, '_blank');
  };

  const copyLink = async () => {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-2">
      <button onClick={shareTwitter} className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:text-accent transition-colors cursor-pointer">&#x1D54F; Share</button>
      <button onClick={shareLinkedIn} className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:text-accent transition-colors cursor-pointer">LinkedIn</button>
      <button onClick={copyLink} className="glass-subtle px-3 py-1.5 rounded-lg text-xs font-mono hover:text-accent transition-colors cursor-pointer">
        {copied ? "Copied!" : "Copy Link"}
      </button>
    </div>
  );
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

interface ToolDetail {
  name: string;
  url: string;
  description: string;
  category: string;
  service_type: string;
  clarvia_score: number;
  rating: string;
  dimensions: Record<string, { score: number; max: number }>;
  scan_id: string;
  source: string;
  tags: string[];
  type_config: Record<string, unknown> | null;
  last_scanned: string | null;
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  mcp_server: { label: "MCP Server", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  api: { label: "API", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  cli_tool: { label: "CLI Tool", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  skill: { label: "Skill", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  general: { label: "General", color: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
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

interface SimilarTool {
  name: string;
  scan_id: string;
  clarvia_score: number;
  service_type: string;
  url: string;
}

function QuickInstall({ tool }: { tool: ToolDetail }) {
  const [copied, setCopied] = useState(false);

  let command = "";
  let label = "";

  if (tool.service_type === "mcp_server") {
    const pkg = tool.type_config?.npm_package as string | undefined;
    command = pkg
      ? `npx -y ${pkg}`
      : `claude mcp add ${tool.name.toLowerCase().replace(/[^a-z0-9-]/g, "-")}`;
    label = "Add to Claude Code";
  } else if (tool.service_type === "cli_tool") {
    command =
      (tool.type_config?.install_command as string) ||
      `npm install ${tool.name}`;
    label = "Install CLI";
  } else if (tool.service_type === "api") {
    command = (tool.type_config?.base_url as string) || tool.url;
    label = "API Endpoint";
  }

  if (!command) return null;

  const copy = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-card rounded-xl p-4">
      <h3 className="text-sm font-semibold mb-3">{label}</h3>
      <div className="flex items-center gap-2">
        <code className="flex-1 bg-black/30 px-3 py-2 rounded-lg text-xs font-mono text-accent overflow-x-auto">
          {command}
        </code>
        <button
          onClick={copy}
          className="glass-subtle px-3 py-2 rounded-lg text-xs font-mono cursor-pointer hover:text-accent transition-colors"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
    </div>
  );
}

function SimilarTools({ scanId }: { scanId: string }) {
  const [similar, setSimilar] = useState<SimilarTool[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/v1/similar/${scanId}?limit=5`)
      .then((r) => r.json())
      .then((data) => setSimilar(data.similar || []))
      .catch(() => setSimilar([]))
      .finally(() => setIsLoading(false));
  }, [scanId]);

  if (isLoading) {
    return (
      <div className="glass-card rounded-xl p-4">
        <h3 className="text-sm font-semibold mb-3">Similar Tools</h3>
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 bg-card-border/20 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (similar.length === 0) return null;

  const typeShortLabels: Record<string, string> = {
    mcp_server: "MCP",
    api: "API",
    cli_tool: "CLI",
    skill: "Skill",
    general: "General",
  };

  return (
    <div className="glass-card rounded-xl p-4">
      <h3 className="text-sm font-semibold mb-3">Similar Tools</h3>
      <div className="space-y-2">
        {similar.map((t) => (
          <Link
            key={t.scan_id}
            href={t.scan_id.startsWith("tool_") ? `/tool/${t.scan_id}` : `/scan/${t.scan_id}`}
            className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-card-border/10 hover:bg-card-border/20 transition-colors group"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs font-medium truncate group-hover:text-accent transition-colors">
                {t.name}
              </span>
              <span className="text-[10px] font-mono text-muted/50">
                {typeShortLabels[t.service_type] || t.service_type}
              </span>
            </div>
            <span
              className={`text-xs font-mono font-bold flex-shrink-0 ${
                t.clarvia_score >= 70
                  ? "text-score-green"
                  : t.clarvia_score >= 40
                  ? "text-score-yellow"
                  : "text-score-red"
              }`}
            >
              {t.clarvia_score}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function ToolDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [tool, setTool] = useState<ToolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (tool) {
      document.title = `${tool.name} — Clarvia Score ${tool.clarvia_score}`;
    }
  }, [tool]);

  useEffect(() => {
    if (!id) return;
    fetch(`${API_BASE}/v1/services/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error("Tool not found");
        return r.json();
      })
      .then(setTool)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !tool) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-muted">{error || "Tool not found"}</p>
        <Link href="/tools" className="text-accent hover:underline text-sm">
          Back to Tools
        </Link>
      </div>
    );
  }

  const typeInfo = TYPE_LABELS[tool.service_type] || TYPE_LABELS.general;
  const tc = tool.type_config || {};

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-card-border/50 backdrop-blur-xl bg-background/80">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
              <Image src="/logos/clarvia-icon.svg" alt="Clarvia" width={30} height={30} className="group-hover:scale-110 transition-transform duration-200" unoptimized />
              <span className="font-semibold text-base tracking-tight text-foreground">clarvia</span>
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
                href="/compare"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Compare
              </Link>
              <Link
                href="/docs"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Docs
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-muted/60 font-mono mb-6">
          <Link href="/tools" className="hover:text-accent">Tools</Link>
          <span>/</span>
          <span className="text-muted">{tool.name}</span>
        </div>

        {/* Hero */}
        <div className="glass-strong rounded-2xl p-8 mb-6">
          <div className="flex flex-col sm:flex-row items-start justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className={`text-xs font-mono px-2 py-1 rounded border ${typeInfo.color}`}>
                  {typeInfo.label}
                </span>
                <span className="text-xs text-muted/50 font-mono">{tool.category}</span>
              </div>
              <div className="flex items-center gap-3 mb-2">
                {getFaviconUrl(tool.url) ? (
                  <img
                    src={getFaviconUrl(tool.url)!}
                    alt=""
                    width={32}
                    height={32}
                    className="w-8 h-8 rounded-lg bg-card-border/30 p-1 object-contain"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <div className="w-8 h-8 rounded-lg bg-card-border/40 flex items-center justify-center">
                    <span className="text-sm font-bold text-muted/70">{tool.name.charAt(0).toUpperCase()}</span>
                  </div>
                )}
                <h1 className="text-2xl font-bold tracking-tight">{tool.name}</h1>
              </div>
              {tool.description && (
                <p className="text-muted leading-relaxed max-w-xl">{stripHtml(tool.description)}</p>
              )}
            </div>
            <div className={`flex-shrink-0 px-5 py-4 rounded-xl border text-center ${scoreBg(tool.clarvia_score)}`}>
              <div className={`text-3xl font-bold font-mono ${scoreColor(tool.clarvia_score)}`}>
                {tool.clarvia_score}
              </div>
              <div className="text-xs text-muted mt-1">{tool.rating}</div>
            </div>
          </div>

          {/* Share */}
          <div className="mb-4">
            <ShareButtons url={`https://clarvia.art/tool/${id}`} title={`${tool.name} — Clarvia Score ${tool.clarvia_score}/100`} />
          </div>

          {/* URL + Quick actions */}
          <div className="flex flex-wrap items-center gap-3">
            {tool.url && (
              <a
                href={tool.url.startsWith("http") ? tool.url : `https://${tool.url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-accent hover:underline font-mono flex items-center gap-1"
              >
                {tool.url.replace(/^https?:\/\//, "").slice(0, 60)}
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                </svg>
              </a>
            )}
            {tool.source && (
              <span className="text-[10px] text-muted/40 font-mono px-2 py-0.5 rounded bg-card-border/20">
                {tool.source.replace("collected:", "")}
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Score breakdown */}
          <div className="glass-card rounded-xl p-6">
            <h2 className="text-sm font-semibold mb-4">Score Breakdown</h2>
            <div className="space-y-3">
              {Object.entries(tool.dimensions).map(([key, val]) => {
                const dimScore = typeof val === "object" ? val.score : val;
                const dimMax = typeof val === "object" ? val.max : 25;
                const pct = (dimScore / dimMax) * 100;
                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs font-mono font-medium">
                        {dimScore}/{dimMax}
                      </span>
                    </div>
                    <div className="h-1.5 bg-card-border/30 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${pct}%`,
                          background: pct >= 70 ? "#22c55e" : pct >= 40 ? "#eab308" : "#ef4444",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Connection info */}
          <div className="glass-card rounded-xl p-6">
            <h2 className="text-sm font-semibold mb-4">Connection Info</h2>
            {Object.keys(tc).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(tc).map(([key, val]) => (
                  <div key={key}>
                    <span className="text-[10px] text-muted/50 font-mono uppercase">{key}</span>
                    <div className="mt-1 text-xs font-mono bg-card-border/20 rounded-lg px-3 py-2 break-all">
                      {typeof val === "string" ? val : JSON.stringify(val, null, 2)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted/50">No connection info available.</p>
            )}

            {/* Tags */}
            {tool.tags && tool.tags.length > 0 && (
              <div className="mt-4 pt-4 border-t border-card-border/30">
                <span className="text-[10px] text-muted/50 font-mono uppercase">Tags</span>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {tool.tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-[10px] font-mono px-2 py-0.5 rounded bg-card-border/30 text-muted/70"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick Install + Similar + Compare */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <div className="space-y-4">
            <QuickInstall tool={tool} />
            <Link
              href={`/compare?ids=${tool.scan_id}`}
              className="glass-subtle rounded-xl p-4 flex items-center justify-center gap-2 hover:border-accent/30 transition-all group block text-center"
            >
              <svg className="w-4 h-4 text-muted group-hover:text-accent transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
              </svg>
              <span className="text-sm text-muted group-hover:text-accent transition-colors">
                Compare with others
              </span>
            </Link>
          </div>
          <SimilarTools scanId={tool.scan_id} />
        </div>

        {/* Badge Embed */}
        <div className="mt-6">
          <BadgeEmbed toolId={id} />
        </div>

        {/* Back */}
        <div className="mt-8 text-center">
          <Link href="/tools" className="text-sm text-muted hover:text-accent transition-colors">
            &larr; Back to Tool Directory
          </Link>
        </div>
      </main>
    </div>
  );
}
