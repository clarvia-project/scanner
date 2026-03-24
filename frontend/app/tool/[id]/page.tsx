"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

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

export default function ToolDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [tool, setTool] = useState<ToolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
              <Link href="/tools" className="text-sm text-accent font-medium">Tools</Link>
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">Leaderboard</Link>
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
              <h1 className="text-2xl font-bold tracking-tight mb-2">{tool.name}</h1>
              {tool.description && (
                <p className="text-muted leading-relaxed max-w-xl">{tool.description}</p>
              )}
            </div>
            <div className={`flex-shrink-0 px-5 py-4 rounded-xl border text-center ${scoreBg(tool.clarvia_score)}`}>
              <div className={`text-3xl font-bold font-mono ${scoreColor(tool.clarvia_score)}`}>
                {tool.clarvia_score}
              </div>
              <div className="text-xs text-muted mt-1">{tool.rating}</div>
            </div>
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
