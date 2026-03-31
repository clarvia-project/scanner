"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

// ----- Types -----

interface Dimension {
  score: number;
  max: number;
}

interface Recommendation {
  title: string;
  description: string;
  priority: string;
}

interface TypeConfig {
  npm_package?: string;
  endpoint_url?: string;
  transport?: string;
  tools?: string[];
  file_url?: string;
  compatible_agents?: string[];
  package_manager?: string;
  package_name?: string;
  binary_name?: string;
  usage_example?: string;
  openapi_url?: string;
  auth_method?: string;
  base_url?: string;
}

interface ServiceData {
  id: string;
  name: string;
  url: string;
  description: string;
  category: string;
  service_type?: string;
  type_config?: TypeConfig;
  github_url?: string;
  tags?: string[];
  clarvia_score?: number | null;
  scan_status?: string;
  rating?: string;
  dimensions?: {
    api_accessibility: Dimension;
    data_structuring: Dimension;
    agent_compatibility: Dimension;
    trust_signals: Dimension;
  };
  recommendations?: Recommendation[];
  scan_history?: { date: string; score: number }[];
  created_at?: string;
}

interface FeedbackStats {
  total_uses: number;
  success_rate: number;
  avg_latency_ms: number;
}

// ----- Helpers -----

function scoreColor(score: number): string {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function scoreGlowClass(score: number): string {
  if (score >= 70) return "glow-green";
  if (score >= 40) return "glow-yellow";
  return "glow-red";
}

function scoreBgGradient(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bar-gradient-green";
  if (pct >= 0.4) return "bar-gradient-yellow";
  return "bar-gradient-red";
}

const TYPE_BADGE_STYLES: Record<string, string> = {
  mcp_server: "bg-purple-500/15 text-purple-400 border-purple-500/25",
  skill: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  cli_tool: "bg-orange-500/15 text-orange-400 border-orange-500/25",
  api: "bg-blue-500/15 text-blue-400 border-blue-500/25",
  general: "bg-gray-500/15 text-gray-400 border-gray-500/25",
};

const TYPE_LABELS: Record<string, string> = {
  mcp_server: "MCP Server",
  skill: "Skill",
  cli_tool: "CLI Tool",
  api: "API",
  general: "General",
};

function TypeBadge({ type }: { type: string }) {
  const style = TYPE_BADGE_STYLES[type] || TYPE_BADGE_STYLES.general;
  const label = TYPE_LABELS[type] || "General";
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-lg text-xs font-mono uppercase tracking-wider border ${style}`}>
      {label}
    </span>
  );
}

// ----- Sparkline SVG -----

function Sparkline({ data, width = 200, height = 40 }: { data: number[]; width?: number; height?: number }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Last point dot */}
      {data.length > 0 && (() => {
        const lastX = width;
        const lastY = height - ((data[data.length - 1] - min) / range) * (height - 4) - 2;
        return <circle cx={lastX} cy={lastY} r={3} fill="var(--accent)" />;
      })()}
    </svg>
  );
}

// ----- Copy button -----

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="shrink-0 px-3 py-2 rounded-lg text-xs font-medium transition-all border border-card-border hover:border-accent/30 text-muted hover:text-accent"
      title="Copy to clipboard"
    >
      {copied ? (
        <svg className="w-4 h-4 text-score-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
        </svg>
      )}
    </button>
  );
}

// ----- Dimension Progress Bar -----

function DimensionBar({ label, score, max }: { label: string; score: number; max: number }) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted font-medium">{label}</span>
        <span className="font-mono text-foreground">{score}/{max}</span>
      </div>
      <div className="h-2 bg-card-border/50 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${scoreBgGradient(score, max)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ----- Integrate Section -----

function IntegrateSection({ service }: { service: ServiceData }) {
  const [activeTab, setActiveTab] = useState<string>("primary");
  const serviceType = service.service_type || "general";
  const config = service.type_config;
  const npmPackage = config?.npm_package || `@${service.name.toLowerCase().replace(/\s+/g, "-")}`;
  const serviceName = service.name.toLowerCase().replace(/\s+/g, "_");
  const badgeUrl = `https://clarvia-api.onrender.com/api/badge/${service.id}`;

  const cicdSnippet = `- uses: clarvia/aeo-check@v1
  with:
    url: ${service.url}
    min-score: 70`;

  let tabs: { id: string; label: string; content: string }[] = [];

  if (serviceType === "mcp_server") {
    const claudeDesktopSnippet = `{
  "mcpServers": {
    "${serviceName}": {
      "command": "npx",
      "args": ["${npmPackage}"]
    }
  }
}`;
    const langchainSnippet = `from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "${serviceName}": {
        "command": "npx",
        "args": ["${npmPackage}"]
    }
})

tools = await client.get_tools()`;
    const badgeSnippet = `![AEO Score](${badgeUrl})`;

    tabs = [
      { id: "claude_desktop", label: "Claude Desktop", content: claudeDesktopSnippet },
      { id: "langchain", label: "LangChain", content: langchainSnippet },
      { id: "cicd", label: "CI/CD Gate", content: cicdSnippet },
      { id: "badge", label: "Badge", content: badgeSnippet },
    ];
  } else if (serviceType === "api") {
    const openaiToolsSnippet = `tools = [{
  "type": "function",
  "function": {
    "name": "call_${serviceName}",
    "description": "${service.description?.slice(0, 100) || `Call ${service.name} API`}",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The query to send to ${service.name}"
        }
      },
      "required": ["query"]
    }
  }
}]`;
    const badgeSnippet = `![AEO Score](${badgeUrl})`;

    tabs = [
      { id: "openai_tools", label: "OpenAI Tools", content: openaiToolsSnippet },
      { id: "cicd", label: "CI/CD Gate", content: cicdSnippet },
      { id: "badge", label: "Badge", content: badgeSnippet },
    ];
  } else {
    tabs = [
      { id: "cicd", label: "CI/CD Gate", content: cicdSnippet },
    ];
  }

  if (tabs.length === 0) return null;

  const activeTabData = tabs.find((t) => t.id === activeTab) || tabs[0];
  const currentTab = activeTabData || tabs[0];

  return (
    <div className="glass-card rounded-2xl p-6">
      <p className="text-xs text-muted uppercase tracking-wider font-medium mb-4">Integrate</p>

      {/* Tab buttons */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all border ${
              (activeTab === tab.id || (activeTab === "primary" && tab.id === tabs[0].id))
                ? "bg-accent/10 text-accent border-accent/30"
                : "text-muted border-card-border hover:text-foreground hover:border-card-border/60"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Code block */}
      <div className="relative group">
        <pre className="bg-card-bg/80 rounded-xl p-4 text-xs font-mono text-foreground overflow-x-auto leading-relaxed">
          {currentTab.content}
        </pre>
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <CopyButton text={currentTab.content} />
        </div>
      </div>

      {/* Badge preview */}
      {currentTab.id === "badge" && (
        <div className="mt-3 flex items-center gap-3">
          <span className="text-xs text-muted">Preview:</span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={badgeUrl}
            alt="AEO Score Badge"
            className="h-5"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </div>
      )}
    </div>
  );
}

// ----- Main Page -----

export default function ServiceDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [service, setService] = useState<ServiceData | null>(null);
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [shareMsg, setShareMsg] = useState("");

  useEffect(() => {
    if (!id) return;

    const fetchService = fetch(`${API_BASE}/v1/profiles/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Service not found");
        return res.json();
      })
      .then((data) => setService(data))
      .catch((err) => setError(err.message));

    const fetchStats = fetch(`${API_BASE}/v1/feedback/${id}/stats`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => data && setStats(data))
      .catch(() => {});

    Promise.all([fetchService, fetchStats]).finally(() => setLoading(false));
  }, [id]);

  function handleShare() {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
      setShareMsg("Link copied!");
      setTimeout(() => setShareMsg(""), 2000);
    });
  }

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen bg-gradient-mesh">
        <header className="sticky top-0 z-40 border-b border-card-border/50 backdrop-blur-xl bg-background/80">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
              <Image src="/logos/clarvia-icon.svg" alt="Clarvia" width={32} height={32} className="rounded-full" />
              <span className="font-semibold text-base tracking-tight text-foreground">clarvia</span>
            </Link>
          </div>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !service) {
    return (
      <div className="flex flex-col min-h-screen bg-gradient-mesh">
        <header className="sticky top-0 z-40 border-b border-card-border/50 backdrop-blur-xl bg-background/80">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
              <Image src="/logos/clarvia-icon.svg" alt="Clarvia" width={32} height={32} className="rounded-full" />
              <span className="font-semibold text-base tracking-tight text-foreground">clarvia</span>
            </Link>
          </div>
        </header>
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <p className="text-muted text-sm">{error || "Service not found"}</p>
              <Link
                href="/tools"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Tools
              </Link>          <Link href="/leaderboard" className="text-accent text-sm hover:underline">Back to Leaderboard</Link>
        </div>
      </div>
    );
  }

  const serviceType = service.service_type || "general";
  const config = service.type_config;

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
                href="/docs"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Docs
              </Link>
            </nav>
          </div>
          <span className="text-xs text-muted/60 font-mono hidden sm:inline">v1.0</span>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-12">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-muted mb-8">
              <Link
                href="/tools"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Tools
              </Link>          <Link href="/leaderboard" className="hover:text-foreground transition-colors">Leaderboard</Link>
          <span>/</span>
          <span className="text-foreground">{service.name}</span>
        </div>

        {/* Service Header */}
        <div className="flex flex-col sm:flex-row items-start gap-6 mb-10">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight truncate">{service.name}</h1>
              <TypeBadge type={serviceType} />
            </div>
            <a
              href={service.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent hover:underline font-mono break-all"
            >
              {service.url}
            </a>
            <p className="text-muted text-sm mt-3 max-w-2xl">{service.description}</p>
            {service.tags && service.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {service.tags.map((tag) => (
                  <span key={tag} className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-card-border/30 text-muted">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={handleShare}
            className="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium border border-card-border hover:border-accent/30 text-muted hover:text-accent transition-all"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
            </svg>
            {shareMsg || "Share"}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Score + Dimensions */}
          <div className="lg:col-span-1 space-y-6">
            {/* AEO Score */}
            {service.clarvia_score != null ? (
              <div className="glass-card rounded-2xl p-6 text-center">
                <p className="text-xs text-muted uppercase tracking-wider font-medium mb-3">AEO Score</p>
                <div className={`text-6xl font-mono font-bold ${scoreColor(service.clarvia_score)} ${scoreGlowClass(service.clarvia_score)}`}>
                  {service.clarvia_score}
                </div>
                {service.rating && (
                  <div className={`inline-block mt-3 px-3 py-1 rounded-lg text-xs font-mono uppercase tracking-wider border ${
                    service.rating === "Exceptional" || service.rating === "Strong"
                      ? "bg-score-green/10 text-score-green border-score-green/20"
                      : service.rating === "Moderate" || service.rating === "Good"
                        ? "bg-score-yellow/10 text-score-yellow border-score-yellow/20"
                        : "bg-score-red/10 text-score-red border-score-red/20"
                  }`}>
                    {service.rating}
                  </div>
                )}
              </div>
            ) : (
              <div className="glass-card rounded-2xl p-6 text-center space-y-4">
                <p className="text-xs text-muted uppercase tracking-wider font-medium">AEO Score</p>
                <p className="text-sm text-muted">
                  {service.scan_status === "scan_failed"
                    ? "스캔 실패"
                    : "AEO 스코어 분석 대기중"}
                </p>
                <a
                  href={`https://clarvia.art/?url=${encodeURIComponent(service.url)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium btn-gradient text-white transition-all"
                >
                  이 서비스 스캔하기
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                </a>
              </div>
            )}

            {/* Dimensions */}
            {service.dimensions && (
              <div className="glass-card rounded-2xl p-6 space-y-4">
                <p className="text-xs text-muted uppercase tracking-wider font-medium">Dimensions</p>
                <DimensionBar label="API Accessibility" score={service.dimensions.api_accessibility.score} max={service.dimensions.api_accessibility.max} />
                <DimensionBar label="Data Structuring" score={service.dimensions.data_structuring.score} max={service.dimensions.data_structuring.max} />
                <DimensionBar label="Agent Compatibility" score={service.dimensions.agent_compatibility.score} max={service.dimensions.agent_compatibility.max} />
                <DimensionBar label="Trust Signals" score={service.dimensions.trust_signals.score} max={service.dimensions.trust_signals.max} />
              </div>
            )}

            {/* Feedback Stats */}
            {stats && (
              <div className="glass-card rounded-2xl p-6">
                <p className="text-xs text-muted uppercase tracking-wider font-medium mb-4">Usage Stats</p>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center">
                    <div className="text-lg font-mono font-bold text-foreground">{stats.total_uses.toLocaleString()}</div>
                    <div className="text-[10px] text-muted uppercase tracking-wider">Uses</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-mono font-bold text-score-green">{stats.success_rate}%</div>
                    <div className="text-[10px] text-muted uppercase tracking-wider">Success</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-mono font-bold text-foreground">{stats.avg_latency_ms}ms</div>
                    <div className="text-[10px] text-muted uppercase tracking-wider">Latency</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Connection Info + History + Guide */}
          <div className="lg:col-span-2 space-y-6">
            {/* Connection Info */}
            {config && serviceType !== "general" && (
              <div className="glass-card rounded-2xl p-6">
                <p className="text-xs text-muted uppercase tracking-wider font-medium mb-4">Connection Info</p>

                {serviceType === "mcp_server" && (
                  <div className="space-y-4">
                    {config.npm_package && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">Install</p>
                        <div className="flex items-center gap-2 bg-card-bg/60 border border-card-border rounded-xl px-4 py-3">
                          <code className="flex-1 text-sm font-mono text-foreground">npm install {config.npm_package}</code>
                          <CopyButton text={`npm install ${config.npm_package}`} />
                        </div>
                      </div>
                    )}
                    {config.endpoint_url && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">Endpoint</p>
                        <div className="flex items-center gap-2 bg-card-bg/60 border border-card-border rounded-xl px-4 py-3">
                          <code className="flex-1 text-sm font-mono text-accent break-all">{config.endpoint_url}</code>
                          <CopyButton text={config.endpoint_url} />
                        </div>
                      </div>
                    )}
                    {config.transport && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-muted">Transport:</span>
                        <span className="font-mono text-foreground px-2 py-0.5 bg-card-border/30 rounded">{config.transport}</span>
                      </div>
                    )}
                    {config.tools && config.tools.length > 0 && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">Available Tools</p>
                        <div className="flex flex-wrap gap-1.5">
                          {config.tools.map((tool) => (
                            <span key={tool} className="px-2.5 py-1 rounded-lg text-xs font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                              {tool}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {serviceType === "skill" && (
                  <div className="space-y-4">
                    {config.file_url && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">Skill File</p>
                        <div className="flex items-center gap-2 bg-card-bg/60 border border-card-border rounded-xl px-4 py-3">
                          <a href={config.file_url} target="_blank" rel="noopener noreferrer" className="flex-1 text-sm font-mono text-accent hover:underline break-all">
                            {config.file_url}
                          </a>
                          <CopyButton text={config.file_url} />
                        </div>
                      </div>
                    )}
                    {config.compatible_agents && config.compatible_agents.length > 0 && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">Compatible Agents</p>
                        <div className="flex flex-wrap gap-1.5">
                          {config.compatible_agents.map((agent) => (
                            <span key={agent} className="px-2.5 py-1 rounded-lg text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {agent}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {serviceType === "cli_tool" && (
                  <div className="space-y-4">
                    {config.package_name && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">Install</p>
                        <div className="flex items-center gap-2 bg-card-bg/60 border border-card-border rounded-xl px-4 py-3">
                          <code className="flex-1 text-sm font-mono text-foreground">
                            {config.package_manager || "npm"} install {config.package_name}
                          </code>
                          <CopyButton text={`${config.package_manager || "npm"} install ${config.package_name}`} />
                        </div>
                      </div>
                    )}
                    {config.binary_name && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-muted">Binary:</span>
                        <code className="font-mono text-foreground px-2 py-0.5 bg-card-border/30 rounded">{config.binary_name}</code>
                      </div>
                    )}
                    {config.usage_example && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">Usage</p>
                        <pre className="bg-card-bg/60 border border-card-border rounded-xl px-4 py-3 text-xs font-mono text-foreground/80 whitespace-pre-wrap overflow-x-auto">
                          {config.usage_example}
                        </pre>
                      </div>
                    )}
                  </div>
                )}

                {serviceType === "api" && (
                  <div className="space-y-4">
                    {config.openapi_url && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">OpenAPI Spec</p>
                        <div className="flex items-center gap-2 bg-card-bg/60 border border-card-border rounded-xl px-4 py-3">
                          <a href={config.openapi_url} target="_blank" rel="noopener noreferrer" className="flex-1 text-sm font-mono text-accent hover:underline break-all">
                            {config.openapi_url}
                          </a>
                          <CopyButton text={config.openapi_url} />
                        </div>
                      </div>
                    )}
                    {config.base_url && (
                      <div>
                        <p className="text-xs text-muted mb-1.5">Base URL</p>
                        <div className="flex items-center gap-2 bg-card-bg/60 border border-card-border rounded-xl px-4 py-3">
                          <code className="flex-1 text-sm font-mono text-foreground break-all">{config.base_url}</code>
                          <CopyButton text={config.base_url} />
                        </div>
                      </div>
                    )}
                    {config.auth_method && config.auth_method !== "none" && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-muted">Authentication:</span>
                        <span className="font-mono text-foreground px-2 py-0.5 bg-card-border/30 rounded capitalize">
                          {config.auth_method.replace("_", " ")}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Integrate Section */}
            <IntegrateSection service={service} />

            {/* Scan History Sparkline */}
            {service.scan_history && service.scan_history.length > 1 && (
              <div className="glass-card rounded-2xl p-6">
                <p className="text-xs text-muted uppercase tracking-wider font-medium mb-4">Score History</p>
                <div className="flex items-end gap-4">
                  <Sparkline data={service.scan_history.map((h) => h.score)} width={400} height={60} />
                  <div className="text-right shrink-0">
                    <div className="text-xs text-muted">{service.scan_history.length} scans</div>
                    <div className="text-xs text-muted/50">
                      Last: {new Date(service.scan_history[service.scan_history.length - 1].date).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Recommendations */}
            {service.recommendations && service.recommendations.length > 0 && (
              <div className="glass-card rounded-2xl p-6">
                <p className="text-xs text-muted uppercase tracking-wider font-medium mb-4">Improvement Guide</p>
                <div className="space-y-3">
                  {service.recommendations.map((rec, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 p-3 rounded-xl bg-card-bg/40 border border-card-border/30"
                    >
                      <span className={`shrink-0 mt-0.5 w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold ${
                        rec.priority === "high"
                          ? "bg-score-red/20 text-score-red"
                          : rec.priority === "medium"
                            ? "bg-score-yellow/20 text-score-yellow"
                            : "bg-card-border/50 text-muted"
                      }`}>
                        {i + 1}
                      </span>
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-foreground">{rec.title}</div>
                        <div className="text-xs text-muted mt-0.5">{rec.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* GitHub Link */}
            {service.github_url && (
              <a
                href={service.github_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 glass-card rounded-2xl p-5 hover:border-accent/30 transition-all group"
              >
                <svg className="w-5 h-5 text-muted group-hover:text-foreground transition-colors" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                </svg>
                <span className="text-sm text-muted group-hover:text-foreground transition-colors font-mono truncate">
                  {service.github_url.replace("https://github.com/", "")}
                </span>
                <svg className="w-4 h-4 text-muted group-hover:text-accent transition-colors ml-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                </svg>
              </a>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border/50 px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <div className="flex items-center gap-3">
            <Image src="/logos/clarvia-icon.svg" alt="Clarvia" width={24} height={24} className="rounded-full" />
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
