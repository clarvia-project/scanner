"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";

// Public-facing API URL shown in documentation examples.
// This is intentionally the production URL, not the env-based API_BASE.
const API_DOCS_BASE = "https://api.clarvia.art";

/* ────────── Types ────────── */

interface Endpoint {
  method: "GET" | "POST";
  path: string;
  title: string;
  description: string;
  auth?: boolean;
  params?: { name: string; in: "query" | "body" | "header" | "path"; type: string; required: boolean; description: string }[];
  curl: string;
  response: string;
  rateLimit: string;
}

interface Section {
  id: string;
  title: string;
  description: string;
  color: string;
  endpoints: Endpoint[];
}

/* ────────── Endpoint data ────────── */

const SECTIONS: Section[] = [
  {
    id: "quickstart",
    title: "Public API",
    description: "No authentication required. Generous rate limits for exploration.",
    color: "text-blue-400",
    endpoints: [
      {
        method: "POST",
        path: "/api/scan",
        title: "Scan URL",
        description: "Run a full AEO scan on any URL. Returns a detailed Clarvia Score breakdown across all dimensions.",
        params: [
          { name: "url", in: "body", type: "string", required: true, description: "The URL to scan (e.g. \"stripe.com\")" },
        ],
        curl: `curl -X POST ${API_DOCS_BASE}/api/scan \\
  -H "Content-Type: application/json" \\
  -d '{"url": "stripe.com"}'`,
        response: `{
  "scan_id": "abc123",
  "url": "https://stripe.com",
  "service_name": "stripe.com",
  "clarvia_score": 72,
  "rating": "Moderate",
  "dimensions": {
    "api_accessibility": { "score": 20, "max": 25, "sub_factors": {...} },
    "data_structuring": { "score": 18, "max": 25, "sub_factors": {...} },
    "agent_compatibility": { "score": 17, "max": 25, "sub_factors": {...} },
    "trust_signals": { "score": 17, "max": 25, "sub_factors": {...} }
  }
}`,
        rateLimit: "10 req/min per IP",
      },
      {
        method: "GET",
        path: "/api/v1/score",
        title: "Get Score",
        description: "Retrieve the Clarvia Score for a single URL. Uses cached/prebuilt data when available, runs a live scan otherwise.",
        params: [
          { name: "url", in: "query", type: "string", required: true, description: "Domain or URL to score (e.g. \"stripe.com\")" },
        ],
        curl: `curl "${API_DOCS_BASE}/api/v1/score?url=stripe.com"`,
        response: `{
  "url": "https://stripe.com",
  "service_name": "stripe.com",
  "clarvia_score": 72,
  "rating": "Moderate",
  "dimensions": {
    "api_accessibility": { "score": 20, "max": 25 },
    "data_structuring": { "score": 18, "max": 25 },
    "agent_compatibility": { "score": 17, "max": 25 },
    "trust_signals": { "score": 17, "max": 25 }
  },
  "scan_id": "abc123",
  "source": "prebuilt"
}`,
        rateLimit: "30 req/min per IP",
      },
      {
        method: "GET",
        path: "/api/v1/leaderboard",
        title: "Leaderboard",
        description: "Get the ranked list of all scanned services, sorted by Clarvia Score descending. Supports pagination.",
        params: [
          { name: "category", in: "query", type: "string", required: false, description: "Filter by category (e.g. \"ai_llm\", \"crypto\", \"devtools\")" },
          { name: "limit", in: "query", type: "integer", required: false, description: "Results per page (default: 50)" },
          { name: "offset", in: "query", type: "integer", required: false, description: "Pagination offset (default: 0)" },
        ],
        curl: `curl "${API_DOCS_BASE}/api/v1/leaderboard?limit=10"`,
        response: `{
  "services": [
    {
      "service_name": "Replicate",
      "url": "https://replicate.com",
      "clarvia_score": 80,
      "rating": "Strong",
      "scan_id": "rep_001"
    }
  ],
  "total": 42,
  "offset": 0,
  "limit": 10
}`,
        rateLimit: "60 req/min per IP",
      },
      {
        method: "GET",
        path: "/api/v1/compare",
        title: "Compare Services",
        description: "Compare 2-5 services side by side. Pass comma-separated URLs. Each service is scored and returned with dimension breakdowns.",
        params: [
          { name: "urls", in: "query", type: "string", required: true, description: "Comma-separated URLs (2-5), e.g. \"stripe.com,replicate.com\"" },
        ],
        curl: `curl "${API_DOCS_BASE}/api/v1/compare?urls=stripe.com,replicate.com"`,
        response: `{
  "comparison": [
    {
      "url": "https://stripe.com",
      "service_name": "stripe.com",
      "clarvia_score": 72,
      "rating": "Moderate",
      "dimensions": {...}
    },
    {
      "url": "https://replicate.com",
      "service_name": "replicate.com",
      "clarvia_score": 80,
      "rating": "Strong",
      "dimensions": {...}
    }
  ]
}`,
        rateLimit: "10 req/min per IP",
      },
      {
        method: "GET",
        path: "/api/v1/methodology",
        title: "Methodology",
        description: "Returns the full scoring methodology as structured JSON, including all dimensions, sub-factors, weights, and rationale.",
        params: [],
        curl: `curl "${API_DOCS_BASE}/api/v1/methodology"`,
        response: `{
  "version": "1.1",
  "updated": "2026-03-25",
  "total_score": 100,
  "dimensions": {
    "api_accessibility": {
      "max": 25,
      "description": "How easily agents can reach your API",
      "sub_factors": {
        "endpoint_existence": { "max": 7, "description": "..." },
        "rate_limit_info": { "max": 6, "description": "..." }
      }
    }
  },
  "onchain_bonus": { "max": 10 }
}`,
        rateLimit: "120 req/min per IP (cached)",
      },
      {
        method: "GET",
        path: "/api/v1/mcp-scan",
        title: "MCP Server Scan",
        description: "Scan an MCP server by URL, npm package name, or GitHub repo. Checks registry presence, tool count, and compatibility.",
        params: [
          { name: "identifier", in: "query", type: "string", required: true, description: "MCP server URL, npm package, or GitHub repo" },
        ],
        curl: `curl "${API_DOCS_BASE}/api/v1/mcp-scan?identifier=@anthropic/mcp-server-fetch"`,
        response: `{
  "identifier": "@anthropic/mcp-server-fetch",
  "found_in": ["mcp.so", "smithery.ai"],
  "tool_count": 3,
  "has_readme": true,
  "has_install_instructions": true,
  "mcp_score": 8,
  "mcp_max": 10,
  "details": {...}
}`,
        rateLimit: "10 req/min per IP",
      },
      {
        method: "GET",
        path: "/api/v1/history",
        title: "Scan History",
        description: "Get historical scan results for a URL, showing score changes over time.",
        params: [
          { name: "url", in: "query", type: "string", required: true, description: "The URL to look up history for" },
          { name: "limit", in: "query", type: "integer", required: false, description: "Max results (default: 20, max: 100)" },
        ],
        curl: `curl "${API_DOCS_BASE}/api/v1/history?url=stripe.com&limit=5"`,
        response: `{
  "url": "https://stripe.com",
  "scans": [
    {
      "scan_id": "abc123",
      "clarvia_score": 72,
      "rating": "Moderate",
      "scanned_at": "2026-03-24T10:30:00Z"
    },
    {
      "scan_id": "abc100",
      "clarvia_score": 68,
      "rating": "Moderate",
      "scanned_at": "2026-03-20T08:00:00Z"
    }
  ],
  "total": 2
}`,
        rateLimit: "30 req/min per IP",
      },
      {
        method: "POST",
        path: "/api/v1/fix",
        title: "Fix Suggestions",
        description: "Generate stack-specific code templates to fix a scan issue. No LLM calls — uses pre-written, production-ready templates.",
        params: [
          { name: "sub_factor", in: "body", type: "string", required: true, description: "The sub-factor to fix (e.g. \"rate_limit_info\", \"cors_headers\")" },
          { name: "stack", in: "body", type: "string", required: true, description: "Tech stack: \"python\", \"nodejs\", or \"go\"" },
          { name: "context", in: "body", type: "object", required: false, description: "Optional context from the scan result" },
        ],
        curl: `curl -X POST ${API_DOCS_BASE}/api/v1/fix \\
  -H "Content-Type: application/json" \\
  -d '{"sub_factor": "rate_limit_info", "stack": "python"}'`,
        response: `{
  "sub_factor": "rate_limit_info",
  "stack": "python",
  "title": "Add X-RateLimit-* headers (FastAPI)",
  "code": "from fastapi import FastAPI\\n...",
  "install": "pip install fastapi",
  "estimated_time": "15 min",
  "potential_gain": 6
}`,
        rateLimit: "20 req/min per IP",
      },
      {
        method: "GET",
        path: "/api/badge/{scan_id}",
        title: "Score Badge",
        description: "Get an embeddable SVG badge for a scan result. Use in READMEs, docs, or websites to display your Clarvia Score.",
        params: [
          { name: "scan_id", in: "path", type: "string", required: true, description: "The scan ID from a previous scan result" },
        ],
        curl: `curl "${API_DOCS_BASE}/api/badge/abc123"`,
        response: `<!-- Returns SVG image -->
<svg xmlns="http://www.w3.org/2000/svg" ...>
  <text>Clarvia Score: 72</text>
</svg>

<!-- Embed in Markdown: -->
![Clarvia Score](${API_DOCS_BASE}/api/badge/abc123)`,
        rateLimit: "120 req/min per IP (cached)",
      },
    ],
  },
  {
    id: "authenticated",
    title: "Authenticated API",
    description: "Requires X-Clarvia-Key header. Higher rate limits and advanced features.",
    color: "text-purple-400",
    endpoints: [
      {
        method: "POST",
        path: "/api/scan/authenticated",
        title: "Authenticated Scan",
        description: "Run a deeper scan using your own API credentials. Tests actual response structure, error handling, and headers with 3 probe requests. Credentials are never logged or stored.",
        auth: true,
        params: [
          { name: "url", in: "body", type: "string", required: true, description: "The API URL to probe" },
          { name: "api_key", in: "body", type: "string", required: true, description: "Your API key (e.g. \"Bearer sk-xxx\")" },
          { name: "header_name", in: "body", type: "string", required: false, description: "Auth header name (default: \"Authorization\")" },
        ],
        curl: `curl -X POST ${API_DOCS_BASE}/api/scan/authenticated \\
  -H "Content-Type: application/json" \\
  -H "X-Clarvia-Key: clv_your_key_here" \\
  -d '{
    "url": "https://api.example.com/v1",
    "api_key": "Bearer sk-xxx",
    "header_name": "Authorization"
  }'`,
        response: `{
  "auth_scan_report": {
    "url": "https://api.example.com/v1",
    "auth_method": "bearer_token",
    "response_structure": {
      "status_code": 200,
      "content_type": "application/json",
      "is_json": true,
      "has_typed_fields": true
    },
    "error_quality": {
      "status_code": 404,
      "is_structured_json": true,
      "has_error_code": true,
      "has_error_message": true,
      "quality": "structured"
    },
    "headers_found": [
      "content-type",
      "x-ratelimit-limit",
      "x-ratelimit-remaining",
      "x-request-id"
    ]
  }
}`,
        rateLimit: "5 req/min per API key",
      },
      {
        method: "POST",
        path: "/api/v1/keys",
        title: "Create API Key",
        description: "Generate a new Clarvia API key. The full key is shown only once in the response. Store it securely.",
        params: [
          { name: "email", in: "body", type: "string", required: true, description: "Your email address" },
          { name: "plan", in: "body", type: "string", required: false, description: "Plan tier (default: \"free\")" },
        ],
        curl: `curl -X POST ${API_DOCS_BASE}/api/v1/keys \\
  -H "Content-Type: application/json" \\
  -d '{"email": "dev@example.com"}'`,
        response: `{
  "key": "clv_abc123def456...",
  "key_id": "clv_abc123",
  "plan": "free",
  "rate_limit": 10
}`,
        rateLimit: "3 req/hour per IP",
      },
      {
        method: "GET",
        path: "/api/v1/keys/validate",
        title: "Validate API Key",
        description: "Check if an API key is valid and see its associated plan and rate limit.",
        auth: true,
        params: [
          { name: "X-Clarvia-Key", in: "header", type: "string", required: true, description: "The API key to validate" },
        ],
        curl: `curl "${API_DOCS_BASE}/api/v1/keys/validate" \\
  -H "X-Clarvia-Key: clv_your_key_here"`,
        response: `{
  "valid": true,
  "key_id": "clv_abc123",
  "plan": "free",
  "rate_limit": 10
}`,
        rateLimit: "30 req/min per API key",
      },
    ],
  },
  {
    id: "traffic",
    title: "Traffic Monitoring",
    description: "Track how AI agents interact with your API in real time.",
    color: "text-cyan-400",
    endpoints: [
      {
        method: "POST",
        path: "/api/v1/traffic/register",
        title: "Register for Monitoring",
        description: "Register your API URL for agent traffic monitoring. Returns a tracking ID and middleware code snippets for Python, Node.js, and Go.",
        params: [
          { name: "url", in: "body", type: "string", required: true, description: "Your API base URL" },
          { name: "email", in: "body", type: "string", required: true, description: "Contact email for reports" },
        ],
        curl: `curl -X POST ${API_DOCS_BASE}/api/v1/traffic/register \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://api.example.com", "email": "dev@example.com"}'`,
        response: `{
  "tracking_id": "trk_abc123",
  "url": "https://api.example.com",
  "email": "dev@example.com",
  "created_at": "2026-03-24T10:30:00Z",
  "existing": false,
  "middleware_snippets": {
    "python": "# FastAPI middleware\\n...",
    "nodejs": "// Express middleware\\n...",
    "go": "// net/http middleware\\n..."
  }
}`,
        rateLimit: "5 req/hour per IP",
      },
      {
        method: "POST",
        path: "/api/v1/traffic/ingest",
        title: "Ingest Events",
        description: "Receive traffic events from your installed middleware. Called automatically by the middleware running on your server.",
        params: [
          { name: "tracking_id", in: "body", type: "string", required: true, description: "Your tracking ID from registration" },
          { name: "user_agent", in: "body", type: "string", required: true, description: "The request User-Agent string" },
          { name: "path", in: "body", type: "string", required: false, description: "Request path (default: \"/\")" },
          { name: "method", in: "body", type: "string", required: false, description: "HTTP method (default: \"GET\")" },
        ],
        curl: `curl -X POST ${API_DOCS_BASE}/api/v1/traffic/ingest \\
  -H "Content-Type: application/json" \\
  -d '{
    "tracking_id": "trk_abc123",
    "user_agent": "anthropic-ai/1.0",
    "path": "/api/v1/data",
    "method": "GET"
  }'`,
        response: `{
  "status": "ok"
}`,
        rateLimit: "1000 req/min per tracking_id",
      },
      {
        method: "GET",
        path: "/api/v1/traffic/stats",
        title: "Traffic Stats",
        description: "Get agent traffic analytics for a registered tracking ID. Shows agent types, request counts, and trends.",
        params: [
          { name: "tracking_id", in: "query", type: "string", required: true, description: "Your tracking ID" },
          { name: "days", in: "query", type: "integer", required: false, description: "Lookback period in days (default: 7, max: 90)" },
        ],
        curl: `curl "${API_DOCS_BASE}/api/v1/traffic/stats?tracking_id=trk_abc123&days=7"`,
        response: `{
  "tracking_id": "trk_abc123",
  "period_days": 7,
  "total_agent_requests": 1423,
  "unique_agents": 5,
  "top_agents": [
    { "agent": "anthropic-ai", "requests": 890 },
    { "agent": "openai-gpt", "requests": 412 }
  ],
  "daily_breakdown": [
    { "date": "2026-03-24", "requests": 234 },
    { "date": "2026-03-23", "requests": 198 }
  ]
}`,
        rateLimit: "30 req/min per tracking_id",
      },
    ],
  },
  {
    id: "ci-cd",
    title: "CI/CD Integration",
    description: "Automate AEO scanning in your deployment pipeline. SARIF export + GitHub Actions.",
    color: "text-orange-400",
    endpoints: [
      {
        method: "GET" as const,
        path: "/api/scan/{scan_id}/sarif",
        title: "SARIF Export",
        description: "Download scan results in SARIF 2.1.0 format for GitHub Code Scanning, VS Code SARIF Viewer, or any SARIF-compatible tool.",
        params: [
          { name: "scan_id", in: "path" as const, type: "string", required: true, description: "The scan ID from a completed scan" },
        ],
        curl: `# Step 1: Run a scan
SCAN_ID=$(curl -s -X POST ${API_DOCS_BASE}/api/scan \\
  -H "Content-Type: application/json" \\
  -d '{"url":"stripe.com"}' | jq -r '.scan_id')

# Step 2: Download SARIF report
curl "${API_DOCS_BASE}/api/scan/$SCAN_ID/sarif" \\
  -o report.sarif.json`,
        response: `{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": { "driver": { "name": "Clarvia AEO Scanner" } },
    "results": [
      {
        "ruleId": "aeo/api-accessibility",
        "level": "warning",
        "message": { "text": "Rate limit headers not exposed" },
        "properties": { "score": 2, "maxScore": 6 }
      }
    ]
  }]
}`,
        rateLimit: "30 req/min",
      },
      {
        method: "POST" as const,
        path: "GitHub Actions Workflow",
        title: "GitHub Actions — AEO Check on Push",
        description: "Add this workflow to .github/workflows/aeo-check.yml to automatically scan your API on every push and upload results to GitHub Code Scanning.",
        params: [],
        curl: `# .github/workflows/aeo-check.yml
name: AEO Check
on: [push, pull_request]

jobs:
  aeo-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Run AEO Scan
        id: scan
        run: |
          RESULT=$(curl -s -X POST https://api.clarvia.art/api/scan \\
            -H "Content-Type: application/json" \\
            -d '{"url":"\${{ vars.API_URL }}"}')
          echo "scan_id=$(echo $RESULT | jq -r '.scan_id')" >> $GITHUB_OUTPUT
          SCORE=$(echo $RESULT | jq -r '.clarvia_score')
          echo "AEO Score: $SCORE"
          if [ "$SCORE" -lt 60 ]; then
            echo "::warning::AEO Score $SCORE is below threshold (60)"
          fi

      - name: Download SARIF
        run: |
          curl -s "https://api.clarvia.art/api/scan/\${{ steps.scan.outputs.scan_id }}/sarif" \\
            -o results.sarif.json

      - name: Upload SARIF to GitHub
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif.json`,
        response: `# After setup, every push will:
# 1. Scan your API for AEO readiness
# 2. Upload SARIF results to GitHub Code Scanning
# 3. Show warnings if score drops below threshold
#
# View results in your repo's Security tab → Code scanning alerts`,
        rateLimit: "N/A",
      },
    ],
  },
];

/* ────────── Components ────────── */

function MethodBadge({ method }: { method: "GET" | "POST" }) {
  const color = method === "GET" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400";
  return (
    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${color}`}>
      {method}
    </span>
  );
}

function AuthBadge() {
  return (
    <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-400">
      AUTH
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="absolute top-2 right-2 text-xs px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-muted hover:text-foreground transition-colors font-mono"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

function EndpointCard({ ep }: { ep: Endpoint }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center gap-3 text-left hover:bg-white/[0.02] transition-colors"
      >
        <MethodBadge method={ep.method} />
        {ep.auth && <AuthBadge />}
        <code className="text-sm font-mono text-foreground flex-1">{ep.path}</code>
        <span className="text-xs text-muted hidden sm:inline">{ep.title}</span>
        <svg
          className={`w-4 h-4 text-muted transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-card-border/50">
          <p className="text-sm text-muted pt-4">{ep.description}</p>

          {/* Parameters */}
          {ep.params && ep.params.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-foreground/80 uppercase tracking-wider mb-2">Parameters</h4>
              <div className="space-y-1">
                {ep.params.map((p) => (
                  <div key={p.name} className="flex items-start gap-2 text-xs">
                    <code className="text-accent bg-accent/10 px-1.5 py-0.5 rounded shrink-0">{p.name}</code>
                    <span className="text-muted/60 shrink-0">({p.in})</span>
                    <span className="text-muted/60 shrink-0">{p.type}</span>
                    {p.required && <span className="text-score-red shrink-0">required</span>}
                    <span className="text-muted">{p.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Request */}
          <div>
            <h4 className="text-xs font-semibold text-foreground/80 uppercase tracking-wider mb-2">Request</h4>
            <div className="relative">
              <pre className="bg-black/40 rounded-lg px-4 py-3 text-xs font-mono text-foreground/80 overflow-x-auto leading-relaxed">
                {ep.curl}
              </pre>
              <CopyButton text={ep.curl} />
            </div>
          </div>

          {/* Response */}
          <div>
            <h4 className="text-xs font-semibold text-foreground/80 uppercase tracking-wider mb-2">Response</h4>
            <div className="relative">
              <pre className="bg-black/40 rounded-lg px-4 py-3 text-xs font-mono text-foreground/80 overflow-x-auto leading-relaxed max-h-64 overflow-y-auto">
                {ep.response}
              </pre>
              <CopyButton text={ep.response} />
            </div>
          </div>

          {/* Rate Limit */}
          <div className="flex items-center gap-2 text-xs text-muted">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Rate limit: {ep.rateLimit}
          </div>
        </div>
      )}
    </div>
  );
}

function SideNav({ sections, activeSection }: { sections: Section[]; activeSection: string }) {
  return (
    <nav className="hidden lg:block sticky top-24 w-48 shrink-0 space-y-1">
      <a href="#quickstart-section" className={`block text-xs px-3 py-1.5 rounded transition-colors ${activeSection === "quickstart-section" ? "text-foreground bg-white/5" : "text-muted hover:text-foreground"}`}>
        Quickstart
      </a>
      {sections.map((s) => (
        <a
          key={s.id}
          href={`#${s.id}`}
          className={`block text-xs px-3 py-1.5 rounded transition-colors ${activeSection === s.id ? "text-foreground bg-white/5" : "text-muted hover:text-foreground"}`}
        >
          {s.title}
        </a>
      ))}
      <a href="#versioning" className={`block text-xs px-3 py-1.5 rounded transition-colors ${activeSection === "versioning" ? "text-foreground bg-white/5" : "text-muted hover:text-foreground"}`}>
        API Versioning
      </a>
      <a href="#cicd" className={`block text-xs px-3 py-1.5 rounded transition-colors ${activeSection === "cicd" ? "text-foreground bg-white/5" : "text-muted hover:text-foreground"}`}>
        CI/CD Integration
      </a>
      <a href="#errors" className={`block text-xs px-3 py-1.5 rounded transition-colors ${activeSection === "errors" ? "text-foreground bg-white/5" : "text-muted hover:text-foreground"}`}>
        Error Handling
      </a>
    </nav>
  );
}

/* ────────── CI/CD Section ────────── */

const GITHUB_ACTION_YAML = `name: AEO Score Check
on: [pull_request]

jobs:
  aeo-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check AEO Score
        run: |
          RESULT=$(curl -s -H "X-Clarvia-Key: \${{ secrets.CLARVIA_API_KEY }}" \\
            -X POST https://clarvia-api.onrender.com/api/v1/ci/check \\
            -H "Content-Type: application/json" \\
            -d '{"url": "\${{ vars.API_URL }}", "min_score": 60}')
          PASSED=$(echo $RESULT | jq -r '.passed')
          SCORE=$(echo $RESULT | jq -r '.score')
          echo "AEO Score: $SCORE"
          if [ "$PASSED" != "true" ]; then
            echo "::error::AEO Score $SCORE is below minimum threshold"
            exit 1
          fi`;

const CI_CURL_EXAMPLE = `curl -s -X POST ${API_DOCS_BASE}/api/v1/ci/check \\
  -H "X-Clarvia-Key: clv_your_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "api.example.com",
    "min_score": 60,
    "required_dimensions": {
      "api_accessibility": 15,
      "agent_compatibility": 10
    }
  }'`;

function CICDSection() {
  const [yamlCopied, setYamlCopied] = useState(false);

  return (
    <section id="cicd" className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-emerald-400">CI/CD Integration</h2>
        <p className="text-sm text-muted">
          Block PR merges when your AEO score drops below a threshold. Keep your API agent-ready on every deploy.
        </p>
      </div>

      {/* Setup steps */}
      <div className="glass-card rounded-xl px-6 py-6 space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold">Setup in 3 steps</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <span className="shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center justify-center">1</span>
            <div className="flex-1">
              <p className="text-sm text-foreground/90 font-medium">Generate an API key</p>
              <div className="relative mt-2">
                <pre className="bg-black/40 rounded-lg px-4 py-3 text-xs font-mono text-foreground/80">
{`curl -X POST ${API_DOCS_BASE}/api/v1/keys \\
  -H "Content-Type: application/json" \\
  -d '{"email": "ci@yourteam.com"}'`}
                </pre>
                <CopyButton text={`curl -X POST ${API_DOCS_BASE}/api/v1/keys -H "Content-Type: application/json" -d '{"email": "ci@yourteam.com"}'`} />
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <span className="shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center justify-center">2</span>
            <div className="flex-1">
              <p className="text-sm text-foreground/90 font-medium">Add to GitHub Secrets</p>
              <p className="text-xs text-muted mt-1">
                Go to <code className="text-accent bg-accent/10 px-1 rounded">Settings &rarr; Secrets and variables &rarr; Actions</code> and add:
              </p>
              <ul className="text-xs text-muted mt-2 space-y-1 ml-4 list-disc">
                <li><code className="text-accent bg-accent/10 px-1 rounded">CLARVIA_API_KEY</code> — your API key from step 1</li>
                <li><code className="text-accent bg-accent/10 px-1 rounded">API_URL</code> (variable) — your API domain (e.g. <code className="text-foreground/70">api.example.com</code>)</li>
              </ul>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <span className="shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center justify-center">3</span>
            <div className="flex-1">
              <p className="text-sm text-foreground/90 font-medium">Add the workflow file</p>
              <p className="text-xs text-muted mt-1">
                Create <code className="text-accent bg-accent/10 px-1 rounded">.github/workflows/aeo-check.yml</code> in your repo:
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* GitHub Actions YAML */}
      <div className="glass-card rounded-xl overflow-hidden">
        <div className="px-5 py-3 flex items-center justify-between border-b border-card-border/50">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-muted" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            <span className="text-sm font-medium">GitHub Actions</span>
            <code className="text-xs text-muted font-mono">.github/workflows/aeo-check.yml</code>
          </div>
          <button
            onClick={() => {
              navigator.clipboard.writeText(GITHUB_ACTION_YAML);
              setYamlCopied(true);
              setTimeout(() => setYamlCopied(false), 2000);
            }}
            className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 transition-colors font-medium"
          >
            {yamlCopied ? "Copied!" : "Copy YAML"}
          </button>
        </div>
        <div className="relative">
          <pre className="bg-black/40 px-5 py-4 text-xs font-mono text-foreground/80 overflow-x-auto leading-relaxed">
            {GITHUB_ACTION_YAML}
          </pre>
        </div>
      </div>

      {/* curl example */}
      <div className="glass-card rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-card-border/50">
          <span className="text-sm font-medium">Direct curl usage</span>
        </div>
        <div className="relative">
          <pre className="bg-black/40 px-5 py-4 text-xs font-mono text-foreground/80 overflow-x-auto leading-relaxed">
            {CI_CURL_EXAMPLE}
          </pre>
          <CopyButton text={CI_CURL_EXAMPLE} />
        </div>
      </div>

      {/* CI endpoint details */}
      <EndpointCard
        ep={{
          method: "POST",
          path: "/api/v1/ci/check",
          title: "CI/CD Gate Check",
          description: "Run a scan and evaluate against minimum thresholds. Returns passed=true only when the overall score meets min_score AND all required_dimensions meet their minimums. Designed for CI/CD pipeline gates.",
          auth: true,
          params: [
            { name: "url", in: "body", type: "string", required: true, description: "The URL to scan" },
            { name: "min_score", in: "body", type: "integer", required: false, description: "Minimum overall score to pass (default: 60)" },
            { name: "required_dimensions", in: "body", type: "object", required: false, description: "Per-dimension minimum scores, e.g. {\"api_accessibility\": 15}" },
          ],
          curl: `curl -X POST ${API_DOCS_BASE}/api/v1/ci/check \\
  -H "X-Clarvia-Key: clv_your_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "api.example.com",
    "min_score": 60,
    "required_dimensions": {
      "api_accessibility": 15,
      "agent_compatibility": 10
    }
  }'`,
          response: `{
  "url": "https://api.example.com",
  "score": 72,
  "min_score": 60,
  "passed": true,
  "dimensions": {
    "api_accessibility": { "score": 20, "max": 25 },
    "data_structuring": { "score": 18, "max": 25 },
    "agent_compatibility": { "score": 18, "max": 25 },
    "trust_signals": { "score": 16, "max": 25 }
  },
  "dimension_checks": {
    "api_accessibility": { "score": 20, "min": 15, "passed": true },
    "agent_compatibility": { "score": 18, "min": 10, "passed": true }
  },
  "badge_url": "https://clarvia.art/api/badge/abc123",
  "details_url": "https://clarvia.art/scan/abc123"
}`,
          rateLimit: "10 req/min per API key",
        }}
      />
    </section>
  );
}

/* ────────── Page ────────── */

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState("quickstart-section");

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

      <div className="flex-1 max-w-6xl mx-auto w-full px-6 py-12 flex gap-10">
        {/* Side nav */}
        <SideNav sections={SECTIONS} activeSection={activeSection} />

        {/* Main content */}
        <main className="flex-1 min-w-0 space-y-12">
          {/* Hero */}
          <div className="text-center space-y-4">
            <h1 className="text-3xl font-bold">API Reference</h1>
            <p className="text-muted max-w-xl mx-auto text-sm leading-relaxed">
              Complete documentation for the Clarvia AEO Scanner API.
              Scan any API, track agent traffic, and optimize your service for AI agents.
            </p>
            <div className="flex items-center justify-center gap-4 text-xs text-muted font-mono">
              <span>Base URL: {API_DOCS_BASE}</span>
              <span>|</span>
              <span>JSON responses</span>
              <span>|</span>
              <span>No SDK required</span>
            </div>
          </div>

          {/* Quickstart */}
          <section id="quickstart-section" className="space-y-6">
            <div className="glass-card rounded-xl px-6 py-6 space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                  <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold">Quickstart: Your first scan in 30 seconds</h2>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center">1</span>
                  <div className="flex-1">
                    <p className="text-sm text-foreground/90 font-medium">Scan your API</p>
                    <div className="relative mt-2">
                      <pre className="bg-black/40 rounded-lg px-4 py-3 text-xs font-mono text-foreground/80">
{`curl -X POST ${API_DOCS_BASE}/api/scan \\
  -H "Content-Type: application/json" \\
  -d '{"url": "your-api.com"}'`}
                      </pre>
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center">2</span>
                  <div className="flex-1">
                    <p className="text-sm text-foreground/90 font-medium">Get your score</p>
                    <p className="text-xs text-muted mt-1">
                      The response includes your Clarvia Score (0-100), rating, and a breakdown across 4 dimensions.
                      Save the <code className="text-accent bg-accent/10 px-1 rounded">scan_id</code> for badges and history.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center">3</span>
                  <div className="flex-1">
                    <p className="text-sm text-foreground/90 font-medium">Get fix suggestions</p>
                    <div className="relative mt-2">
                      <pre className="bg-black/40 rounded-lg px-4 py-3 text-xs font-mono text-foreground/80">
{`curl -X POST ${API_DOCS_BASE}/api/v1/fix \\
  -H "Content-Type: application/json" \\
  -d '{"sub_factor": "rate_limit_info", "stack": "python"}'`}
                      </pre>
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center">4</span>
                  <div className="flex-1">
                    <p className="text-sm text-foreground/90 font-medium">Embed your badge</p>
                    <div className="relative mt-2">
                      <pre className="bg-black/40 rounded-lg px-4 py-3 text-xs font-mono text-foreground/80">
{`![Clarvia Score](${API_DOCS_BASE}/api/badge/YOUR_SCAN_ID)`}
                      </pre>
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center justify-center">5</span>
                  <div className="flex-1">
                    <p className="text-sm text-foreground/90 font-medium">Monitor agent traffic (optional)</p>
                    <p className="text-xs text-muted mt-1">
                      Register at <code className="text-accent bg-accent/10 px-1 rounded">POST /api/v1/traffic/register</code> to get middleware snippets and track how AI agents use your API.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Auth info */}
            <div className="glass-card rounded-xl px-6 py-4 space-y-2">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                </svg>
                Authentication
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                Most endpoints require no authentication. For authenticated endpoints, include your API key in the <code className="text-accent bg-accent/10 px-1 rounded">X-Clarvia-Key</code> header.
                Get a free key at <code className="text-accent bg-accent/10 px-1 rounded">POST /api/v1/keys</code>.
              </p>
              <div className="relative">
                <pre className="bg-black/40 rounded-lg px-4 py-2 text-xs font-mono text-foreground/80">
{`curl -H "X-Clarvia-Key: clv_your_key_here" ${API_DOCS_BASE}/api/v1/keys/validate`}
                </pre>
              </div>
            </div>
          </section>

          {/* API Versioning */}
          <section id="versioning" className="space-y-4">
            <div className="space-y-1">
              <h2 className="text-xl font-semibold text-cyan-400">API Versioning</h2>
              <p className="text-sm text-muted">
                How Clarvia manages API versions, deprecation timelines, and backward compatibility.
              </p>
            </div>

            <div className="glass-card rounded-xl px-6 py-6 space-y-5">
              {/* Current version */}
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-emerald-400">v1</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground/90">Current stable version</p>
                  <p className="text-xs text-muted mt-1">
                    All production endpoints use the <code className="text-accent bg-accent/10 px-1 rounded">/api/v1/</code> prefix.
                    This is the recommended version for all new integrations.
                  </p>
                </div>
              </div>

              {/* Legacy */}
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-amber-400">v0</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground/90">Legacy endpoints (deprecation planned)</p>
                  <p className="text-xs text-muted mt-1">
                    <code className="text-accent bg-accent/10 px-1 rounded">POST /api/scan</code> is a legacy v0 endpoint.
                    It will continue to work but is scheduled for deprecation. Migrate to <code className="text-accent bg-accent/10 px-1 rounded">GET /api/v1/score</code> for new projects.
                  </p>
                </div>
              </div>

              {/* Versioning strategy */}
              <div className="border-t border-card-border/30 pt-4 space-y-3">
                <h4 className="text-xs font-semibold text-foreground/80 uppercase tracking-wider">Versioning Strategy</h4>
                <div className="space-y-2 text-xs text-muted">
                  <div className="flex items-start gap-2">
                    <span className="text-accent shrink-0 mt-0.5">&#9679;</span>
                    <span>All versioned endpoints use the <code className="text-accent bg-accent/10 px-1 rounded">/api/v&#123;N&#125;/</code> URL prefix</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-accent shrink-0 mt-0.5">&#9679;</span>
                    <span>Breaking changes are introduced only in a new major version (e.g. v2)</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-accent shrink-0 mt-0.5">&#9679;</span>
                    <span>Deprecated versions receive a minimum <strong className="text-foreground/80">6-month notice</strong> before removal</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-accent shrink-0 mt-0.5">&#9679;</span>
                    <span>Additive changes (new fields, new endpoints) are non-breaking and added to the current version</span>
                  </div>
                </div>
              </div>

              {/* API-Version header */}
              <div className="border-t border-card-border/30 pt-4 space-y-3">
                <h4 className="text-xs font-semibold text-foreground/80 uppercase tracking-wider">API-Version Response Header</h4>
                <p className="text-xs text-muted leading-relaxed">
                  Every response includes an <code className="text-accent bg-accent/10 px-1 rounded">API-Version</code> header indicating which version served the request.
                  Use this to verify your integration targets the correct version.
                </p>
                <div className="relative">
                  <pre className="bg-black/40 rounded-lg px-4 py-3 text-xs font-mono text-foreground/80 overflow-x-auto leading-relaxed">
{`HTTP/1.1 200 OK
Content-Type: application/json
API-Version: v1
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 29`}
                  </pre>
                </div>
              </div>

              {/* Migration note */}
              <div className="border-t border-card-border/30 pt-4">
                <div className="flex items-start gap-2">
                  <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                  </svg>
                  <p className="text-xs text-muted leading-relaxed">
                    <strong className="text-foreground/80">Migration tip:</strong> If you are using <code className="text-accent bg-accent/10 px-1 rounded">POST /api/scan</code>, switch to <code className="text-accent bg-accent/10 px-1 rounded">GET /api/v1/score?url=...</code> for better caching, simpler integration, and guaranteed long-term support.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Endpoint sections */}
          {SECTIONS.map((section) => (
            <section key={section.id} id={section.id} className="space-y-4">
              <div className="space-y-1">
                <h2 className={`text-xl font-semibold ${section.color}`}>{section.title}</h2>
                <p className="text-sm text-muted">{section.description}</p>
              </div>
              <div className="space-y-3">
                {section.endpoints.map((ep) => (
                  <EndpointCard key={ep.path + ep.method} ep={ep} />
                ))}
              </div>
            </section>
          ))}

          {/* CI/CD Integration */}
          <CICDSection />

          {/* Error handling */}
          <section id="errors" className="space-y-4">
            <h2 className="text-xl font-semibold text-score-red">Error Handling</h2>
            <p className="text-sm text-muted">All errors return JSON with a consistent structure.</p>

            <div className="glass-card rounded-xl px-5 py-4 space-y-3">
              <div className="relative">
                <pre className="bg-black/40 rounded-lg px-4 py-3 text-xs font-mono text-foreground/80">
{`{
  "detail": "Human-readable error message"
}`}
                </pre>
              </div>

              <h4 className="text-xs font-semibold text-foreground/80 uppercase tracking-wider">Status Codes</h4>
              <div className="space-y-1.5 text-xs">
                {[
                  { code: "200", desc: "Success" },
                  { code: "400", desc: "Bad request — missing or invalid parameters" },
                  { code: "401", desc: "Unauthorized — invalid or missing API key" },
                  { code: "404", desc: "Not found — scan ID or resource does not exist" },
                  { code: "422", desc: "Unprocessable — URL is invalid or unreachable" },
                  { code: "429", desc: "Rate limit exceeded — wait and retry" },
                  { code: "500", desc: "Server error — scan failed internally" },
                ].map((s) => (
                  <div key={s.code} className="flex items-center gap-3">
                    <code className={`font-mono font-bold ${
                      s.code === "200" ? "text-emerald-400" : s.code.startsWith("4") ? "text-amber-400" : "text-score-red"
                    }`}>{s.code}</code>
                    <span className="text-muted">{s.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Rate limiting note */}
            <div className="glass-card rounded-xl px-5 py-4 space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
                Rate Limiting
              </h4>
              <p className="text-xs text-muted leading-relaxed">
                Rate limits are per IP for public endpoints and per API key for authenticated endpoints.
                When rate limited, you receive a <code className="text-accent bg-accent/10 px-1 rounded">429</code> status code.
                Check <code className="text-accent bg-accent/10 px-1 rounded">X-RateLimit-Remaining</code> and <code className="text-accent bg-accent/10 px-1 rounded">X-RateLimit-Reset</code> headers to manage your usage.
              </p>
            </div>
          </section>

          {/* Footer CTA */}
          <div className="text-center space-y-3 py-6">
            <p className="text-sm text-muted">Ready to optimize your API for AI agents?</p>
            <div className="flex items-center justify-center gap-3">
              <Link href="/" className="text-sm text-accent hover:underline">Scan your API</Link>
              <span className="text-muted/30">|</span>
              <Link href="/guide" className="text-sm text-accent hover:underline">Optimization Guide</Link>
              <span className="text-muted/30">|</span>
              <Link href="/methodology" className="text-sm text-accent hover:underline">Scoring Methodology</Link>
            </div>
          </div>
        </main>
      </div>

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
            <span>Clarvia &mdash; Discovery &amp; Trust standard for the agent economy</span>
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
