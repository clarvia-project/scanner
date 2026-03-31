"use client";

import Link from "next/link";
import Image from "next/image";

const DIMENSIONS = [
  {
    key: "api_accessibility",
    label: "API Accessibility",
    max: 25,
    color: "text-blue-400",
    bg: "bg-blue-400/10",
    border: "border-blue-400/20",
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
    bg: "bg-purple-400/10",
    border: "border-purple-400/20",
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
    bg: "bg-cyan-400/10",
    border: "border-cyan-400/20",
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
    bg: "bg-emerald-400/10",
    border: "border-emerald-400/20",
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

const AGENT_GRADES = [
  {
    grade: "AGENT_NATIVE",
    range: "80 — 100",
    meaning: "Fully optimized for autonomous AI agent use",
    behavior: "Agents can use this tool autonomously without human configuration",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  {
    grade: "AGENT_FRIENDLY",
    range: "60 — 79",
    meaning: "Good agent support with minor gaps",
    behavior: "Agents can use with some initial configuration or setup",
    color: "text-blue-400",
    bg: "bg-blue-400/10",
  },
  {
    grade: "AGENT_POSSIBLE",
    range: "40 — 59",
    meaning: "Partial agent compatibility",
    behavior: "Agents should use as fallback only; expect friction",
    color: "text-yellow-400",
    bg: "bg-yellow-400/10",
  },
  {
    grade: "AGENT_HOSTILE",
    range: "0 — 39",
    meaning: "Not designed for agent use",
    behavior: "Agents should avoid; high failure rate expected",
    color: "text-red-400",
    bg: "bg-red-400/10",
  },
];

const GATEWAY_RATINGS = [
  { label: "Exceptional", range: "90+", desc: "World-class agent readiness across all dimensions", color: "text-emerald-400" },
  { label: "Excellent", range: "80 — 89", desc: "Production-ready for autonomous agents", color: "text-blue-400" },
  { label: "Strong", range: "65 — 79", desc: "Good with minor gaps to address", color: "text-cyan-400" },
  { label: "Moderate", range: "45 — 64", desc: "Usable but needs improvement in key areas", color: "text-yellow-400" },
  { label: "Basic", range: "25 — 44", desc: "Significant gaps in agent compatibility", color: "text-orange-400" },
  { label: "Low", range: "0 — 24", desc: "Not agent-ready; requires fundamental changes", color: "text-red-400" },
];

const ONCHAIN_BONUS = [
  { name: "Transaction Success Rate", max: 10, desc: "RPC endpoint health and responsiveness for blockchain services" },
  { name: "Real Volume / Chain Coverage", max: 10, desc: "Number of supported chains and WebSocket availability" },
  { name: "Staking / Commitment", max: 5, desc: "SLA, uptime guarantees, enterprise signals" },
];

const CHANGES = [
  { change: "Rate Limit Info: 3 → 6 pts", reason: "#1 cause of agent failures in production (429 errors)" },
  { change: "MCP Server: 10 → 7 pts", reason: "Important but APIs work fine without MCP via OpenAPI specs" },
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
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12 space-y-12">
        {/* Hero */}
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

        {/* Formula Overview */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Formula
          </h2>
          <div className="glass-card rounded-xl px-6 py-5 space-y-4">
            <div className="font-mono text-sm text-center text-foreground leading-relaxed">
              <p>Clarvia Score = API Accessibility (25)</p>
              <p className="text-muted">+</p>
              <p>Data Structuring (25)</p>
              <p className="text-muted">+</p>
              <p>Agent Compatibility (25)</p>
              <p className="text-muted">+</p>
              <p>Trust Signals (25)</p>
              <p className="text-muted mt-2 text-xs">= 100 points base + up to 25 Web3 bonus</p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              {DIMENSIONS.map((dim) => (
                <div
                  key={dim.key}
                  className={`rounded-lg px-3 py-2.5 text-center ${dim.bg} border ${dim.border}`}
                >
                  <p className={`text-lg font-bold font-mono ${dim.color}`}>{dim.max}</p>
                  <p className="text-[10px] text-muted mt-0.5">{dim.label}</p>
                </div>
              ))}
            </div>
          </div>
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

        {/* Web3 / Onchain Bonus */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-amber-400">Web3 Onchain Bonus</h2>
            <span className="text-xs text-muted font-mono">+25 pts max</span>
          </div>
          <div className="glass-card rounded-xl px-6 py-4 space-y-3">
            <p className="text-xs text-muted leading-relaxed">
              Blockchain-specific services receive up to 25 bonus points on top of the base 100.
              Non-blockchain services receive 0 bonus and are not penalized.
            </p>
          </div>
          <div className="glass-card rounded-xl overflow-hidden divide-y divide-card-border/30">
            {ONCHAIN_BONUS.map((sf) => (
              <div key={sf.name} className="px-6 py-3.5 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <span className="text-sm">{sf.name}</span>
                  <p className="text-xs text-muted mt-0.5">{sf.desc}</p>
                </div>
                <span className="text-sm font-mono text-muted shrink-0">{sf.max}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Agent Grades */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Agent Grades
          </h2>
          <p className="text-xs text-muted leading-relaxed">
            Agent grades tell AI agents how to treat a tool. Agents use these grades to make autonomous decisions
            about whether to integrate a service, use it as a fallback, or avoid it entirely.
          </p>
          <div className="glass-card rounded-xl overflow-hidden divide-y divide-card-border/30">
            {AGENT_GRADES.map((g) => (
              <div key={g.grade} className="px-6 py-4">
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`text-sm font-mono font-semibold ${g.color}`}>{g.grade}</span>
                  <span className="text-xs text-muted font-mono">{g.range}</span>
                </div>
                <p className="text-sm text-foreground">{g.meaning}</p>
                <p className="text-xs text-muted mt-1">{g.behavior}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Gateway Ratings */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Gateway Ratings
          </h2>
          <p className="text-xs text-muted leading-relaxed">
            Human-readable quality labels displayed alongside scores. These map directly to the numeric score.
          </p>
          <div className="glass-card rounded-xl overflow-hidden divide-y divide-card-border/30">
            {GATEWAY_RATINGS.map((r) => (
              <div key={r.label} className="px-6 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <span className={`text-sm font-medium ${r.color}`}>{r.label}</span>
                  <p className="text-xs text-muted mt-0.5">{r.desc}</p>
                </div>
                <span className="text-xs text-muted font-mono shrink-0">{r.range}</span>
              </div>
            ))}
          </div>
        </div>

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
            <p>
              Scores are <strong className="text-foreground">deterministic</strong> — the same input always produces the same score.
              All scan data and scoring logic are transparent. No manual overrides, no pay-to-boost.
            </p>
          </div>
        </div>

        {/* How a Scan Works */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            How a Scan Works
          </h2>
          <div className="glass-card rounded-xl px-6 py-5 space-y-3 text-sm text-muted leading-relaxed">
            <p>
              When you submit a URL, Clarvia runs <strong className="text-foreground">11 independent crawlers</strong> in
              parallel — checking endpoints, response headers, documentation, schema definitions, MCP registries,
              and more. The entire scan typically completes in under 30 seconds.
            </p>
            <p>
              Each crawler produces evidence-backed sub-factor scores. These roll up into the four dimension scores,
              which sum to the final Clarvia Score. Every recommendation in the scan report is tied to a specific
              measured gap — no generic advice.
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
