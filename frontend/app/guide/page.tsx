"use client";

import Link from "next/link";
import Image from "next/image";
import { useState, useCallback } from "react";

const STACKS = ["Node.js", "Python", "Go", "Other"] as const;
type Stack = (typeof STACKS)[number];

/* ────────── Code examples per Quick Win per stack ────────── */

const QUICK_WIN_CODE: Record<string, Record<Stack, string>> = {
  "Add X-RateLimit-* headers": {
    "Node.js": `const rateLimit = require("express-rate-limit");

app.use(
  rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    standardHeaders: true, // X-RateLimit-*
    legacyHeaders: false,
  })
);`,
    Python: `from fastapi import FastAPI, Request, Response
from time import time

LIMIT, WINDOW = 100, 900  # 100 req / 15 min
hits: dict[str, list] = {}

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    ip = request.client.host
    now = time()
    hits[ip] = [t for t in hits.get(ip, []) if now - t < WINDOW]
    remaining = LIMIT - len(hits[ip])
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
    response.headers["X-RateLimit-Reset"] = str(int(now + WINDOW))
    hits[ip].append(now)
    return response`,
    Go: `import "golang.org/x/time/rate"

var limiter = rate.NewLimiter(rate.Every(time.Second), 10)

func rateLimitMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if !limiter.Allow() {
            w.Header().Set("X-RateLimit-Remaining", "0")
            http.Error(w, "Too Many Requests", 429)
            return
        }
        w.Header().Set("X-RateLimit-Limit", "10")
        w.Header().Set("X-RateLimit-Remaining",
            fmt.Sprintf("%d", int(limiter.Tokens())))
        next.ServeHTTP(w, r)
    })
}`,
    Other: `# robots.txt — framework-agnostic
# Add these response headers to every API response:
#
#   X-RateLimit-Limit: 100
#   X-RateLimit-Remaining: 97
#   X-RateLimit-Reset: 1710000000
#
# Most frameworks have a rate-limit middleware — check your docs.`,
  },

  "Publish robots.txt allowing AI agents": {
    "Node.js": `// public/robots.txt
User-agent: *
Allow: /api/
Sitemap: https://yourapi.com/sitemap.xml

// .well-known/ai-plugin.json — serve via Express:
app.use("/.well-known", express.static("well-known"));`,
    Python: `# static/.well-known/ai-plugin.json
# robots.txt content:
"""
User-agent: *
Allow: /api/
Sitemap: https://yourapi.com/sitemap.xml
"""

from fastapi.staticfiles import StaticFiles
app.mount("/.well-known", StaticFiles(directory="static/.well-known"))`,
    Go: `// robots.txt content:
// User-agent: *
// Allow: /api/
// Sitemap: https://yourapi.com/sitemap.xml

http.Handle("/.well-known/",
    http.StripPrefix("/.well-known/",
        http.FileServer(http.Dir("./well-known"))))`,
    Other: `# robots.txt — place at site root
User-agent: *
Allow: /api/
Sitemap: https://yourapi.com/sitemap.xml

# .well-known/ai-plugin.json
{
  "schema_version": "v1",
  "name": "YourService",
  "description": "Short description of your API",
  "api": { "type": "openapi", "url": "/openapi.json" }
}`,
  },

  "Add a /health endpoint": {
    "Node.js": `app.get("/health", async (req, res) => {
  try {
    await db.query("SELECT 1");
    res.json({ status: "ok", uptime: process.uptime() });
  } catch (e) {
    res.status(503).json({ status: "error", message: e.message });
  }
});`,
    Python: `@app.get("/health")
async def health():
    try:
        await db.execute("SELECT 1")
        return {"status": "ok", "uptime": time.monotonic()}
    except Exception as e:
        raise HTTPException(503, detail={"status": "error", "msg": str(e)})`,
    Go: `http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
    if err := db.Ping(); err != nil {
        w.WriteHeader(503)
        json.NewEncoder(w).Encode(map[string]string{
            "status": "error", "message": err.Error(),
        })
        return
    }
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
})`,
    Other: `# Health endpoint checklist:
# 1. GET /health — returns {"status": "ok"} or {"status": "error"}
# 2. Check DB connectivity
# 3. Return 200 on success, 503 on failure
# 4. Include uptime or version metadata`,
  },

  "Return structured JSON errors": {
    "Node.js": `app.use((err, req, res, next) => {
  const status = err.status || 500;
  res.status(status).json({
    error: {
      code: err.code || "INTERNAL_ERROR",
      message: err.message,
      docs_url: "https://yourapi.com/docs/errors",
    },
  });
});`,
    Python: `from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    code = getattr(exc, "status_code", 500)
    return JSONResponse(status_code=code, content={
        "error": {
            "code": getattr(exc, "code", "INTERNAL_ERROR"),
            "message": str(exc),
            "docs_url": "https://yourapi.com/docs/errors",
        }
    })`,
    Go: `type APIError struct {
    Code    string \`json:"code"\`
    Message string \`json:"message"\`
    DocsURL string \`json:"docs_url"\`
}

func writeError(w http.ResponseWriter, status int, code, msg string) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(map[string]APIError{
        "error": {Code: code, Message: msg,
            DocsURL: "https://yourapi.com/docs/errors"},
    })
}`,
    Other: `# Every error response should follow this shape:
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Retry after 30s.",
    "docs_url": "https://yourapi.com/docs/errors#rate-limit"
  }
}
# Never return HTML error pages to API consumers.`,
  },

  "Add .well-known/ai-plugin.json": {
    "Node.js": `// well-known/ai-plugin.json
const plugin = {
  schema_version: "v1",
  name: "YourService",
  description: "Short API description for agents",
  api: { type: "openapi", url: "https://yourapi.com/openapi.json" },
  auth: { type: "none" },
};

// Serve it
app.get("/.well-known/ai-plugin.json", (req, res) => res.json(plugin));`,
    Python: `# .well-known/ai-plugin.json
PLUGIN = {
    "schema_version": "v1",
    "name": "YourService",
    "description": "Short API description for agents",
    "api": {"type": "openapi", "url": "https://yourapi.com/openapi.json"},
    "auth": {"type": "none"},
}

@app.get("/.well-known/ai-plugin.json")
async def ai_plugin():
    return PLUGIN`,
    Go: `http.HandleFunc("/.well-known/ai-plugin.json",
    func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(map[string]any{
            "schema_version": "v1",
            "name":           "YourService",
            "description":    "Short API description for agents",
            "api":            map[string]string{"type": "openapi", "url": "/openapi.json"},
            "auth":           map[string]string{"type": "none"},
        })
    })`,
    Other: `# Place this file at /.well-known/ai-plugin.json
{
  "schema_version": "v1",
  "name": "YourService",
  "description": "Short API description for agents",
  "api": {
    "type": "openapi",
    "url": "https://yourapi.com/openapi.json"
  },
  "auth": { "type": "none" }
}`,
  },
};

/* ────────── Code examples per dimension item per stack ────────── */

const DIMENSION_CODE: Record<string, Record<Stack, string>> = {
  // API Accessibility
  "Ensure public reachability": {
    "Node.js": `// Verify your API is publicly reachable
const app = require("express")();
app.listen(process.env.PORT || 3000, "0.0.0.0", () => {
  console.log("Listening on all interfaces");
});`,
    Python: `# Bind to 0.0.0.0 so external traffic can reach you
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)`,
    Go: `log.Fatal(http.ListenAndServe(":8080", mux))
// Ensure firewall allows inbound on this port`,
    Other: `# Checklist:
# 1. Bind to 0.0.0.0, not 127.0.0.1
# 2. Open firewall port
# 3. Verify with: curl -I https://yourapi.com`,
  },
  "Optimize response speed": {
    "Node.js": `const compression = require("compression");
const apicache = require("apicache");

app.use(compression());
app.use(apicache.middleware("5 minutes"));
// Target: < 200ms p50 latency`,
    Python: `from fastapi.middleware.gzip import GZipMiddleware
from cachetools import TTLCache

app.add_middleware(GZipMiddleware, minimum_size=500)
cache = TTLCache(maxsize=1024, ttl=300)`,
    Go: `import "github.com/klauspost/compress/gzhttp"

handler := gzhttp.GzipHandler(mux)
// Add in-memory cache with sync.Map or groupcache`,
    Other: `# Speed checklist:
# - Enable gzip/brotli compression
# - Add response caching (5 min TTL)
# - Use connection pooling for DB`,
  },
  "Document authentication": {
    "Node.js": `// In your OpenAPI spec (openapi.json):
// "securityDefinitions": {
//   "BearerAuth": {
//     "type": "http", "scheme": "bearer"
//   }
// }
app.use((req, res, next) => {
  const token = req.headers.authorization?.split(" ")[1];
  if (!token) return res.status(401).json({ error: "Missing token" });
  next();
});`,
    Python: `from fastapi.security import HTTPBearer
security = HTTPBearer()

@app.get("/protected")
async def protected(token=Depends(security)):
    return {"message": "Authenticated"}`,
    Go: `func authMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        token := r.Header.Get("Authorization")
        if token == "" {
            writeError(w, 401, "UNAUTHORIZED", "Missing token")
            return
        }
        next.ServeHTTP(w, r)
    })
}`,
    Other: `# Auth documentation checklist:
# 1. Add securityDefinitions to OpenAPI spec
# 2. Support Bearer token or API key
# 3. Return 401 with clear error message`,
  },

  // Data Structuring
  "Publish OpenAPI / JSON Schema": {
    "Node.js": `const swaggerJsdoc = require("swagger-jsdoc");
const swaggerUi = require("swagger-ui-express");

const spec = swaggerJsdoc({
  definition: { openapi: "3.0.0", info: { title: "My API", version: "1.0" } },
  apis: ["./routes/*.js"],
});
app.use("/docs", swaggerUi.serve, swaggerUi.setup(spec));`,
    Python: `# FastAPI generates OpenAPI automatically!
# Access at /openapi.json and /docs

from pydantic import BaseModel
class Item(BaseModel):
    name: str
    price: float

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    return item`,
    Go: `// Use swaggo/swag for auto-generation:
// go install github.com/swaggo/swag/cmd/swag@latest
// swag init

// @Summary Get item
// @Produce json
// @Success 200 {object} Item
// @Router /items/{id} [get]
func getItem(w http.ResponseWriter, r *http.Request) {}`,
    Other: `# OpenAPI spec minimum:
# 1. Every endpoint documented
# 2. Request/response schemas typed
# 3. Served at /openapi.json
# 4. Interactive docs at /docs`,
  },
  "Make pricing machine-readable": {
    "Node.js": `app.get("/pricing", (req, res) => {
  res.json({
    plans: [
      { name: "free", price: 0, requests: 1000, unit: "month" },
      { name: "pro", price: 29, requests: 100000, unit: "month" },
    ],
    currency: "USD",
  });
});`,
    Python: `@app.get("/pricing")
async def pricing():
    return {
        "plans": [
            {"name": "free", "price": 0, "requests": 1000, "unit": "month"},
            {"name": "pro", "price": 29, "requests": 100000, "unit": "month"},
        ],
        "currency": "USD",
    }`,
    Go: `http.HandleFunc("/pricing", func(w http.ResponseWriter, r *http.Request) {
    json.NewEncoder(w).Encode(map[string]any{
        "plans": []map[string]any{
            {"name": "free", "price": 0, "requests": 1000},
            {"name": "pro", "price": 29, "requests": 100000},
        }, "currency": "USD",
    })
})`,
    Other: `# Pricing endpoint example response:
{
  "plans": [
    {"name": "free", "price": 0, "requests": 1000},
    {"name": "pro", "price": 29, "requests": 100000}
  ],
  "currency": "USD"
}`,
  },
  "Return structured errors": {
    "Node.js": `app.use((err, req, res, next) => {
  res.status(err.status || 500).json({
    error: {
      code: err.code || "INTERNAL_ERROR",
      message: err.message,
      docs_url: "https://yourapi.com/docs/errors",
    },
  });
});`,
    Python: `@app.exception_handler(Exception)
async def handler(request, exc):
    return JSONResponse(status_code=500, content={
        "error": {"code": "INTERNAL_ERROR", "message": str(exc),
                  "docs_url": "https://yourapi.com/docs/errors"}
    })`,
    Go: `func writeError(w http.ResponseWriter, status int, code, msg string) {
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(map[string]any{
        "error": map[string]string{
            "code": code, "message": msg,
            "docs_url": "https://yourapi.com/docs/errors"},
    })
}`,
    Other: `# Always return JSON errors:
{ "error": { "code": "NOT_FOUND", "message": "...", "docs_url": "..." } }
# Never return HTML error pages to API clients.`,
  },

  // Agent Compatibility
  "Implement MCP support": {
    "Node.js": `import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer({ name: "my-api", version: "1.0.0" });
server.tool("search", { query: z.string() }, async ({ query }) => {
  const results = await search(query);
  return { content: [{ type: "text", text: JSON.stringify(results) }] };
});`,
    Python: `from mcp.server import Server
import mcp.types as types

server = Server("my-api")

@server.list_tools()
async def list_tools():
    return [types.Tool(name="search", description="Search items",
            inputSchema={"type":"object","properties":{"query":{"type":"string"}}})]`,
    Go: `// Use github.com/mark3labs/mcp-go
s := server.NewMCPServer("my-api", "1.0.0")
s.AddTool(mcp.NewTool("search",
    mcp.WithDescription("Search items"),
    mcp.WithString("query", mcp.Required()),
), searchHandler)`,
    Other: `# MCP = Model Context Protocol
# 1. Define tools your API exposes
# 2. Use the official SDK for your language
# 3. Register on MCP registries
# See: https://modelcontextprotocol.io`,
  },
  "Set agent-friendly robot policies": {
    "Node.js": `// Serve robots.txt with AI agent access
app.get("/robots.txt", (req, res) => {
  res.type("text/plain").send(
    "User-agent: *\\nAllow: /api/\\nSitemap: https://yourapi.com/sitemap.xml"
  );
});`,
    Python: `from fastapi.responses import PlainTextResponse

@app.get("/robots.txt")
async def robots():
    return PlainTextResponse(
        "User-agent: *\\nAllow: /api/\\nSitemap: https://yourapi.com/sitemap.xml"
    )`,
    Go: `http.HandleFunc("/robots.txt", func(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "text/plain")
    fmt.Fprint(w, "User-agent: *\\nAllow: /api/\\n")
})`,
    Other: `# robots.txt at your site root:
User-agent: *
Allow: /api/
Sitemap: https://yourapi.com/sitemap.xml`,
  },
  "Register on discovery platforms": {
    "Node.js": `// Serve a .well-known/clarvia.json profile
app.get("/.well-known/clarvia.json", (req, res) => {
  res.json({
    name: "YourService",
    description: "What your API does",
    api_url: "https://yourapi.com",
    openapi_url: "https://yourapi.com/openapi.json",
    contact: "dev@yourapi.com",
  });
});`,
    Python: `@app.get("/.well-known/clarvia.json")
async def clarvia_profile():
    return {
        "name": "YourService",
        "description": "What your API does",
        "api_url": "https://yourapi.com",
        "openapi_url": "https://yourapi.com/openapi.json",
    }`,
    Go: `http.HandleFunc("/.well-known/clarvia.json",
    func(w http.ResponseWriter, r *http.Request) {
        json.NewEncoder(w).Encode(map[string]string{
            "name": "YourService",
            "api_url": "https://yourapi.com",
            "openapi_url": "https://yourapi.com/openapi.json",
        })
    })`,
    Other: `# .well-known/clarvia.json
{
  "name": "YourService",
  "description": "What your API does",
  "api_url": "https://yourapi.com",
  "openapi_url": "https://yourapi.com/openapi.json"
}`,
  },

  // Trust Signals
  "Publish a status page": {
    "Node.js": `app.get("/health", async (req, res) => {
  const checks = {
    db: await checkDb(),
    cache: await checkRedis(),
  };
  const ok = Object.values(checks).every(Boolean);
  res.status(ok ? 200 : 503).json({ status: ok ? "ok" : "degraded", checks });
});`,
    Python: `@app.get("/health")
async def health():
    checks = {"db": await check_db(), "cache": await check_redis()}
    ok = all(checks.values())
    status = 200 if ok else 503
    return JSONResponse(status_code=status,
        content={"status": "ok" if ok else "degraded", "checks": checks})`,
    Go: `http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
    dbOk := db.Ping() == nil
    status := "ok"
    code := 200
    if !dbOk { status = "degraded"; code = 503 }
    w.WriteHeader(code)
    json.NewEncoder(w).Encode(map[string]any{"status": status, "db": dbOk})
})`,
    Other: `# Health check endpoint must:
# 1. Check all critical dependencies (DB, cache, etc.)
# 2. Return 200 + {"status": "ok"} when healthy
# 3. Return 503 + {"status": "degraded"} when not`,
  },
  "Write excellent documentation": {
    "Node.js": `// Use swagger-ui-express for interactive docs
const swaggerUi = require("swagger-ui-express");
const spec = require("./openapi.json");

app.use("/docs", swaggerUi.serve, swaggerUi.setup(spec, {
  customCss: ".swagger-ui .topbar { display: none }",
  tryItOutEnabled: true,
}));`,
    Python: `# FastAPI gives you free interactive docs at:
#   /docs     — Swagger UI
#   /redoc    — ReDoc
# Just define Pydantic models and type hints:

@app.get("/items/{id}", response_model=ItemResponse)
async def get_item(id: int):
    """Get an item by ID. Returns 404 if not found."""
    ...`,
    Go: `// Serve Swagger UI from swaggo:
// go install github.com/swaggo/swag/cmd/swag@latest
import httpSwagger "github.com/swaggo/http-swagger"

mux.Handle("/docs/", httpSwagger.Handler(
    httpSwagger.URL("/openapi.json"),
))`,
    Other: `# Documentation checklist:
# 1. Interactive "Try it" for every endpoint
# 2. Code examples in 3+ languages
# 3. Quickstart guide < 5 minutes
# 4. Error code reference table`,
  },
  "Show active maintenance": {
    "Node.js": `// Serve a machine-readable changelog
app.get("/changelog", (req, res) => {
  res.json({
    latest: "2.1.0",
    updated: "2025-03-20",
    entries: [
      { version: "2.1.0", date: "2025-03-20", changes: ["Added MCP support"] },
      { version: "2.0.1", date: "2025-03-10", changes: ["Fixed rate limit bug"] },
    ],
  });
});`,
    Python: `@app.get("/changelog")
async def changelog():
    return {
        "latest": "2.1.0",
        "updated": "2025-03-20",
        "entries": [
            {"version": "2.1.0", "date": "2025-03-20",
             "changes": ["Added MCP support"]},
        ],
    }`,
    Go: `http.HandleFunc("/changelog", func(w http.ResponseWriter, r *http.Request) {
    json.NewEncoder(w).Encode(map[string]any{
        "latest": "2.1.0", "updated": "2025-03-20",
        "entries": []map[string]any{
            {"version": "2.1.0", "changes": []string{"Added MCP support"}},
        },
    })
})`,
    Other: `# Maintenance signals:
# 1. Machine-readable /changelog endpoint
# 2. GitHub repo with recent commits
# 3. "Last-Modified" or "X-API-Version" header`,
  },
};

/* ────────── Data ────────── */

const DIMENSIONS = [
  {
    key: "api_accessibility",
    label: "API Accessibility",
    max: 25,
    color: "blue",
    description:
      "How easily AI agents can discover, reach, and authenticate with your API endpoints.",
    items: [
      {
        title: "Ensure public reachability",
        points: "Up to 10 pts",
        detail:
          "Your API must return a 2xx response at a publicly accessible URL. Agents need to reach you without manual setup.",
      },
      {
        title: "Optimize response speed",
        points: "Up to 10 pts",
        detail:
          "Target sub-200ms p50 latency. Use CDN, connection pooling, and edge caching. Agents abandon slow APIs.",
      },
      {
        title: "Document authentication",
        points: "Up to 5 pts",
        detail:
          "Publish OpenAPI security schemes. Support Bearer tokens or API keys with clear instructions.",
      },
    ],
  },
  {
    key: "data_structuring",
    label: "Data Structuring",
    max: 25,
    color: "purple",
    description:
      "How well your data is organized for machine consumption — schemas, pricing, and error handling.",
    items: [
      {
        title: "Publish OpenAPI / JSON Schema",
        points: "Up to 10 pts",
        detail:
          "Provide a complete OpenAPI spec with typed schemas for every endpoint. Agents parse these to understand your API.",
      },
      {
        title: "Make pricing machine-readable",
        points: "Up to 5 pts",
        detail:
          "Add a structured pricing endpoint or embed pricing metadata. Agents need to compare costs programmatically.",
      },
      {
        title: "Return structured errors",
        points: "Up to 10 pts",
        detail:
          "Use consistent JSON error format: { error: { code, message, docs_url } }. Never return HTML error pages.",
      },
    ],
  },
  {
    key: "agent_compatibility",
    label: "Agent Compatibility",
    max: 25,
    color: "cyan",
    description:
      "Direct support for AI agent protocols, discovery mechanisms, and robot policies.",
    items: [
      {
        title: "Implement MCP support",
        points: "Up to 10 pts",
        detail:
          "Publish MCP (Model Context Protocol) tool definitions. This is the fastest path to agent integration.",
      },
      {
        title: "Set agent-friendly robot policies",
        points: "Up to 5 pts",
        detail:
          "Allow AI agents in robots.txt. Publish .well-known/ai-plugin.json for ChatGPT/agent discovery.",
      },
      {
        title: "Register on discovery platforms",
        points: "Up to 10 pts",
        detail:
          "List your API on MCP registries, RapidAPI, or publish a .well-known/clarvia.json profile.",
      },
    ],
  },
  {
    key: "trust_signals",
    label: "Trust Signals",
    max: 25,
    color: "emerald",
    description:
      "Signals that help agents (and their users) trust your service — uptime, docs, and freshness.",
    items: [
      {
        title: "Publish a status page",
        points: "Up to 8 pts",
        detail:
          "Use Betteruptime, Instatus, or similar. Expose an API-accessible /health endpoint. Agents check before calling.",
      },
      {
        title: "Write excellent documentation",
        points: "Up to 10 pts",
        detail:
          "Include interactive examples, code snippets in 3+ languages, and a quickstart guide under 5 minutes.",
      },
      {
        title: "Show active maintenance",
        points: "Up to 7 pts",
        detail:
          "Maintain a public changelog. Keep GitHub active with recent commits. Agents prefer actively maintained APIs.",
      },
    ],
  },
];

const QUICK_WINS = [
  { action: "Add X-RateLimit-* headers", effort: "30 min", impact: "+3-5 pts" },
  { action: "Publish robots.txt allowing AI agents", effort: "10 min", impact: "+2-3 pts" },
  { action: "Add a /health endpoint", effort: "1 hour", impact: "+3-5 pts" },
  { action: "Return structured JSON errors", effort: "2 hours", impact: "+5-8 pts" },
  { action: "Add .well-known/ai-plugin.json", effort: "30 min", impact: "+3-5 pts" },
];

/* ────────── Components ────────── */

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [code]);

  return (
    <div className="relative group">
      <button
        onClick={copy}
        className="absolute top-2.5 right-2.5 text-[10px] font-mono px-2 py-1 rounded-md bg-white/5 hover:bg-white/10 text-muted hover:text-foreground transition-colors opacity-0 group-hover:opacity-100"
      >
        {copied ? "Copied!" : "Copy"}
      </button>
      <pre className="bg-[#141c28] rounded-lg p-4 font-mono text-xs text-[#c9d1d9] overflow-x-auto leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function CollapsibleCode({ code, label }: { code: string; label?: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-[11px] font-mono text-accent/70 hover:text-accent transition-colors flex items-center gap-1.5"
      >
        <span className="inline-block transition-transform" style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}>
          &#9654;
        </span>
        {label || "Show code example"}
      </button>
      {open && (
        <div className="mt-2">
          <CodeBlock code={code} />
        </div>
      )}
    </div>
  );
}

/* ────────── Page ────────── */

export default function GuidePage() {
  const [stack, setStack] = useState<Stack>("Node.js");

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
              </Link>              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">
                Leaderboard
              </Link>
              <Link href="/guide" className="text-sm text-foreground font-medium">
                Guide
              </Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">
                Docs
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12 space-y-12">
        {/* Hero */}
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold">AEO Optimization Guide</h1>
          <p className="text-muted max-w-xl mx-auto text-sm leading-relaxed">
            AI Engine Optimization (AEO) makes your service discoverable and usable by AI agents.
            This guide breaks down every scoring dimension with actionable steps.
          </p>
          <Link
            href="/"
            className="inline-block btn-gradient text-white px-6 py-2.5 rounded-xl text-sm font-medium"
          >
            Scan your service first &rarr;
          </Link>
        </div>

        {/* Stack Selector */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs text-muted font-mono">Your stack:</span>
          <div className="flex gap-2">
            {STACKS.map((s) => (
              <button
                key={s}
                onClick={() => setStack(s)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
                  stack === s
                    ? "bg-accent/20 text-accent border border-accent/30"
                    : "bg-white/5 text-muted border border-card-border/30 hover:border-card-border/60 hover:text-foreground"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Agent Framework Integration */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Agent Framework Integration
          </h2>
          <p className="text-sm text-muted">
            Integrate Clarvia AEO scoring directly into your multi-agent workflows.
            Use these examples as LangChain tools, CrewAI agents, or OpenAI function calls.
          </p>
          <div className="space-y-3">
            {/* LangChain */}
            <div className="glass-card rounded-xl px-6 py-5 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">LangChain</h3>
                <span className="text-xs text-accent font-mono">@tool decorator</span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                Wrap the Clarvia API as a LangChain tool. Agents can call it to evaluate any API&apos;s agent-readiness before integration.
              </p>
              <CollapsibleCode
                label="Show LangChain example"
                code={`from langchain.tools import tool
import requests

@tool
def check_api_aeo_score(url: str) -> dict:
    """Check if an API is agent-ready using Clarvia AEO Score"""
    resp = requests.get(f"https://api.clarvia.art/api/v1/score?url={url}")
    data = resp.json()
    score = data["clarvia_score"]
    if score >= 70:
        return {"status": "agent-ready", "score": score}
    return {"status": "needs-improvement", "score": score, "top_fix": data["recommendations"][0]}`}
              />
            </div>

            {/* CrewAI */}
            <div className="glass-card rounded-xl px-6 py-5 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">CrewAI</h3>
                <span className="text-xs text-accent font-mono">@tool + Agent</span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                Define a CrewAI tool and assign it to an API Evaluator agent that finds the most agent-friendly APIs for your crew.
              </p>
              <CollapsibleCode
                label="Show CrewAI example"
                code={`from crewai import Agent, Task
from crewai_tools import tool

@tool("AEO Scanner")
def scan_api(url: str) -> str:
    """Evaluate API agent-readiness score"""
    import requests
    resp = requests.get(f"https://api.clarvia.art/api/v1/score?url={url}")
    return str(resp.json())

api_evaluator = Agent(
    role="API Evaluator",
    goal="Find the most agent-friendly APIs",
    tools=[scan_api]
)`}
              />
            </div>

            {/* OpenAI Function Calling */}
            <div className="glass-card rounded-xl px-6 py-5 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">OpenAI Function Calling</h3>
                <span className="text-xs text-accent font-mono">tools schema</span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                Define the Clarvia API as an OpenAI-compatible function. Works with GPT-4, Claude, and any model that supports tool use.
              </p>
              <CollapsibleCode
                label="Show OpenAI function calling example"
                code={`tools = [{
    "type": "function",
    "function": {
        "name": "check_aeo_score",
        "description": "Check API agent-readiness score via Clarvia",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "API base URL"}},
            "required": ["url"]
        }
    }
}]`}
              />
            </div>
          </div>
        </div>

        {/* Quick Wins */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
            Quick Wins (Under 2 Hours)
          </h2>
          <div className="glass-card rounded-xl overflow-hidden">
            <div className="divide-y divide-card-border/30">
              {QUICK_WINS.map((win, i) => (
                <div key={i} className="px-6 py-4">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-score-green text-xs font-mono font-bold shrink-0">{win.impact}</span>
                      <span className="text-sm truncate">{win.action}</span>
                    </div>
                    <span className="text-xs text-muted shrink-0">{win.effort}</span>
                  </div>
                  {QUICK_WIN_CODE[win.action]?.[stack] && (
                    <CollapsibleCode code={QUICK_WIN_CODE[win.action][stack]} />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Dimension Guides */}
        {DIMENSIONS.map((dim) => (
          <div key={dim.key} className="space-y-4">
            <div className="flex items-center gap-3">
              <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
                {dim.label}
              </h2>
              <span className="text-xs text-muted font-mono">{dim.max} pts max</span>
            </div>
            <p className="text-sm text-muted">{dim.description}</p>
            <div className="space-y-3">
              {dim.items.map((item, i) => (
                <div key={i} className="glass-card rounded-xl px-6 py-5 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold">{item.title}</h3>
                    <span className="text-xs text-accent font-mono">{item.points}</span>
                  </div>
                  <p className="text-xs text-muted leading-relaxed">{item.detail}</p>
                  {DIMENSION_CODE[item.title]?.[stack] && (
                    <CollapsibleCode code={DIMENSION_CODE[item.title][stack]} />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* CTA */}
        <div className="glass-card rounded-xl px-6 py-8 text-center space-y-4">
          <h2 className="text-lg font-bold">Ready to measure your progress?</h2>
          <p className="text-sm text-muted">
            Follow our Quick Wins checklist — most developers improve their score by 15+ points in one afternoon.
          </p>
          <Link
            href="/"
            className="inline-block btn-gradient text-white px-8 py-3 rounded-xl text-sm font-medium"
          >
            Scan Now — Free
          </Link>
        </div>
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
            <span>Clarvia — Discovery &amp; Trust standard for the agent economy</span>
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
