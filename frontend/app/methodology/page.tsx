"use client";

import Link from "next/link";
import Image from "next/image";

const DIMENSIONS = [
  {
    key: "api_accessibility",
    label: "API Accessibility",
    max: 25,
    color: "text-blue-400",
    subs: [
      { name: "Endpoint Existence", max: 7, desc: "Publicly reachable endpoint returning 2xx" },
      { name: "Response Speed", max: 6, desc: "Median response time, target <200ms" },
      { name: "Auth Documentation", max: 3, desc: "OpenAPI security schemes documented" },
      { name: "Rate Limit Transparency", max: 6, desc: "#1 cause of agent failures — X-RateLimit-* headers", highlight: true },
      { name: "API Versioning", max: 1, desc: "API version in URL path or header" },
      { name: "SDK Availability", max: 1, desc: "Official SDKs on PyPI/npm" },
      { name: "Free Tier / Trial", max: 1, desc: "Free tier or trial available" },
    ],
  },
  {
    key: "data_structuring",
    label: "Data Structuring",
    max: 25,
    color: "text-purple-400",
    subs: [
      { name: "Schema Definition", max: 7, desc: "OpenAPI/JSON Schema published with typed models" },
      { name: "Pricing Quantified", max: 5, desc: "Machine-readable pricing information" },
      { name: "Error Structure", max: 5, desc: "Structured JSON errors (RFC 7807 or equivalent)" },
      { name: "Webhook Support", max: 3, desc: "Webhook endpoints or documented webhook system" },
      { name: "Batch API Support", max: 3, desc: "Batch/bulk endpoints for efficient agent operations" },
      { name: "Type Definitions", max: 2, desc: "JSON Schema or TypeScript type definitions published" },
    ],
  },
  {
    key: "agent_compatibility",
    label: "Agent Compatibility",
    max: 25,
    color: "text-cyan-400",
    subs: [
      { name: "MCP Server Exists", max: 7, desc: "Registered on mcp.so, Smithery, or Glama" },
      { name: "robots.txt Agent Policy", max: 5, desc: "Agent-friendly robots.txt with AI agent rules" },
      { name: "Discovery Mechanism", max: 5, desc: "Sitemap, ai-plugin.json, .well-known configs" },
      { name: "Idempotency Support", max: 3, desc: "Idempotency-Key header for safe retries", highlight: true },
      { name: "Pagination Pattern", max: 2, desc: "Consistent cursor/offset pagination" },
      { name: "Streaming Support", max: 3, desc: "SSE/streaming endpoints for real-time data", highlight: true },
    ],
  },
  {
    key: "trust_signals",
    label: "Trust Signals",
    max: 25,
    color: "text-emerald-400",
    subs: [
      { name: "Success Rate & Uptime", max: 6, desc: "Public status page with uptime metrics and history" },
      { name: "Documentation Quality", max: 5, desc: "API reference, guides, code examples, changelogs" },
      { name: "Update Frequency", max: 4, desc: "Active changelog, recent updates within 30-90 days" },
      { name: "Response Consistency", max: 4, desc: "Identical responses across repeated requests" },
      { name: "Error Response Quality", max: 3, desc: "Error includes code, message, and documentation link" },
      { name: "Deprecation Policy", max: 2, desc: "Explicit deprecation/versioning policy documented" },
      { name: "SLA / Uptime Guarantee", max: 1, desc: "Published SLA or uptime commitment" },
    ],
  },
];

const CHANGES = [
  { change: "Rate Limit Info: 3 \u2192 6 pts", reason: "#1 cause of agent failures in production (429 errors)" },
  { change: "MCP Server: 10 \u2192 7 pts", reason: "Important but APIs work fine without MCP via OpenAPI specs" },
  { change: "NEW: Idempotency Support (3 pts)", reason: "Critical for agent retry safety" },
  { change: "NEW: Streaming Support (3 pts)", reason: "Essential for LLM-based API services" },
  { change: "NEW: Pagination Pattern (2 pts)", reason: "Agents need to handle large datasets reliably" },
  { change: "Trust Signals: restructured to 7 sub-factors", reason: "Response consistency, error quality, deprecation policy, and SLA now scored separately" },
  { change: "Data Structuring: restructured to 6 sub-factors", reason: "Added webhook support, batch API, type definitions; removed CORS (moved to informational)" },
];

export default function MethodologyPage() {
  return (
    <div className="flex flex-col min-h-screen bg-gradient-mesh">
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
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">Leaderboard</Link>
              <Link href="/guide" className="text-sm text-muted hover:text-foreground transition-colors">Guide</Link>
              <Link href="/methodology" className="text-sm text-foreground font-medium">Methodology</Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">Docs</Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12 space-y-12">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold">Scoring Methodology</h1>
          <p className="text-muted max-w-xl mx-auto text-sm leading-relaxed">
            How we calculate the Clarvia Score. Weights are based on real-world agent failure frequencies
            and developer pain points — not marketing narratives.
          </p>
          <div className="flex items-center justify-center gap-4 text-xs text-muted font-mono">
            <span>v1.1</span>
            <span>Updated 2026-03-25</span>
            <span>Total: 100 pts + 25 onchain bonus</span>
          </div>
        </div>

        {/* API access note */}
        <div className="glass-card rounded-xl px-6 py-4">
          <p className="text-xs text-muted">
            This methodology is also available as structured JSON at{" "}
            <code className="text-accent bg-accent/10 px-1.5 py-0.5 rounded text-xs">GET /api/v1/methodology</code>
          </p>
        </div>

        {/* Dimensions */}
        {DIMENSIONS.map((dim) => (
          <div key={dim.key} className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className={`text-sm font-semibold ${dim.color}`}>{dim.label}</h2>
              <span className="text-xs text-muted font-mono">{dim.max} pts</span>
            </div>
            <div className="glass-card rounded-xl overflow-hidden divide-y divide-card-border/30">
              {dim.subs.map((sf) => (
                <div key={sf.name} className="px-6 py-3.5 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{sf.name}</span>
                      {sf.highlight && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-mono">NEW</span>
                      )}
                    </div>
                    <p className="text-xs text-muted mt-0.5">{sf.desc}</p>
                  </div>
                  <span className="text-sm font-mono text-muted shrink-0">{sf.max}</span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Weight changes */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            v1.1 Weight Changes
          </h2>
          <div className="glass-card rounded-xl overflow-hidden divide-y divide-card-border/30">
            {CHANGES.map((c, i) => (
              <div key={i} className="px-6 py-3.5">
                <p className="text-sm font-medium">{c.change}</p>
                <p className="text-xs text-muted mt-1">{c.reason}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Philosophy */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Scoring Philosophy
          </h2>
          <div className="glass-card rounded-xl px-6 py-5 space-y-3 text-sm text-muted leading-relaxed">
            <p>
              Clarvia Score measures <strong className="text-foreground">how easily AI agents can discover and use your service</strong>.
              It does not measure company size, product quality, or business viability.
            </p>
            <p>
              Weights are derived from agent-builder pain frequency: we prioritize factors that cause the most
              agent failures in production. Rate limit headers (6pts) outweigh SDK availability (1pt) because
              missing rate limits crash agents, while missing SDKs merely slow integration.
            </p>
            <p>
              MCP support was reduced from 10 to 7 points because well-documented OpenAPI specs enable agent
              integration without MCP. We want to reward all paths to agent compatibility, not just one protocol.
            </p>
          </div>
        </div>

        <div className="text-center">
          <Link
            href="/"
            className="inline-block btn-gradient text-white px-8 py-3 rounded-xl text-sm font-medium"
          >
            Scan Your Service
          </Link>
        </div>
      </main>

      <footer className="border-t border-card-border/50 px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <span>Clarvia — Discovery & Trust standard for the agent economy</span>
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
