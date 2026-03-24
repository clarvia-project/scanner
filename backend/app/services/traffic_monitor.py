"""Agent traffic monitoring for Clarvia.

Flow:
1. User registers URL -> gets tracking_id
2. User installs middleware that detects agent user-agents
3. Middleware POSTs events to /api/v1/traffic/ingest
4. User views stats at /api/v1/traffic/stats?tracking_id=xxx
"""

import hashlib
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Known AI agent user-agent patterns
AGENT_PATTERNS = [
    "claude",
    "anthropic",
    "openai",
    "gpt",
    "cursor",
    "copilot",
    "perplexity",
    "langchain",
    "autogpt",
    "babyagi",
    "crewai",
    "browserbase",
    "playwright-agent",
    "semantic-kernel",
    "chatgpt",
    "cohere",
    "mistral",
    "gemini",
    "devin",
]

INGEST_URL = "https://clarvia-api.onrender.com/api/v1/traffic/ingest"

# In-memory storage (Supabase upgrade later)
_tracking_registry: dict[str, dict] = {}  # tracking_id -> {url, email, created_at}
_traffic_events: dict[str, list[dict]] = defaultdict(list)  # tracking_id -> [{agent, path, method, ts}]


def generate_tracking_id() -> str:
    """Generate a unique tracking ID based on timestamp + random bytes."""
    raw = f"{time.time_ns()}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"trk_{h}"


def detect_agent(user_agent: str) -> str | None:
    """Detect which AI agent sent the request from user-agent string.

    Returns the matched agent pattern name, or None if not an agent.
    """
    if not user_agent:
        return None
    ua_lower = user_agent.lower()
    for pattern in AGENT_PATTERNS:
        if pattern in ua_lower:
            return pattern
    return None


async def register_url(url: str, email: str) -> dict:
    """Register a URL for agent traffic monitoring.

    Returns tracking_id and metadata.
    """
    # Check if already registered (same url + email)
    for tid, info in _tracking_registry.items():
        if info["url"] == url and info["email"] == email:
            return {"tracking_id": tid, **info, "existing": True}

    tracking_id = generate_tracking_id()
    record = {
        "url": url,
        "email": email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _tracking_registry[tracking_id] = record
    return {"tracking_id": tracking_id, **record, "existing": False}


async def ingest_event(tracking_id: str, user_agent: str, path: str, method: str) -> bool:
    """Receive and store a traffic event from user's middleware.

    Returns True if event was recorded, False if tracking_id unknown or not an agent.
    """
    if tracking_id not in _tracking_registry:
        return False

    agent = detect_agent(user_agent)
    if not agent:
        return False

    _traffic_events[tracking_id].append({
        "agent": agent,
        "path": path,
        "method": method.upper() if method else "GET",
        "ts": time.time(),
        "user_agent": user_agent[:200],
    })
    return True


async def get_stats(tracking_id: str, days: int = 7) -> dict | None:
    """Get agent traffic analytics for a tracking_id.

    Returns None if tracking_id not found.
    """
    if tracking_id not in _tracking_registry:
        return None

    info = _tracking_registry[tracking_id]
    cutoff = time.time() - (days * 86400)
    events = [e for e in _traffic_events.get(tracking_id, []) if e["ts"] >= cutoff]

    # Agent breakdown
    agent_counter: dict[str, dict] = {}
    for e in events:
        agent = e["agent"]
        if agent not in agent_counter:
            agent_counter[agent] = {"requests": 0, "last_seen": 0}
        agent_counter[agent]["requests"] += 1
        if e["ts"] > agent_counter[agent]["last_seen"]:
            agent_counter[agent]["last_seen"] = e["ts"]

    agent_breakdown = [
        {
            "agent": agent,
            "requests": data["requests"],
            "last_seen": datetime.fromtimestamp(data["last_seen"], tz=timezone.utc).isoformat() if data["last_seen"] > 0 else None,
        }
        for agent, data in sorted(agent_counter.items(), key=lambda x: x[1]["requests"], reverse=True)
    ]

    # Daily trend
    daily: dict[str, int] = Counter()
    for e in events:
        day = datetime.fromtimestamp(e["ts"], tz=timezone.utc).strftime("%Y-%m-%d")
        daily[day] += 1

    daily_trend = [
        {"date": d, "requests": c}
        for d, c in sorted(daily.items())
    ]

    # Top paths
    path_counter: Counter = Counter()
    for e in events:
        path_counter[e["path"]] += 1

    top_paths = [p for p, _ in path_counter.most_common(10)]

    return {
        "tracking_id": tracking_id,
        "url": info["url"],
        "period": f"{days}d",
        "total_agent_requests": len(events),
        "unique_agents": len(agent_counter),
        "agent_breakdown": agent_breakdown,
        "daily_trend": daily_trend,
        "top_paths": top_paths,
    }


def get_middleware_snippets(tracking_id: str) -> dict[str, str]:
    """Return working middleware code snippets for Python, Node.js, and Go."""

    snippet_python = f'''# Add to your FastAPI app
import asyncio
import aiohttp
from starlette.middleware.base import BaseHTTPMiddleware

AGENT_PATTERNS = {AGENT_PATTERNS!r}
CLARVIA_TRACKING_ID = "{tracking_id}"
CLARVIA_INGEST_URL = "{INGEST_URL}"

class ClarviAgentTracker(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        ua = request.headers.get("user-agent", "").lower()
        if any(p in ua for p in AGENT_PATTERNS):
            # Fire-and-forget: don't slow down the response
            asyncio.create_task(self._report(ua, str(request.url.path), request.method))
        return response

    async def _report(self, ua: str, path: str, method: str):
        try:
            async with aiohttp.ClientSession() as s:
                await s.post(CLARVIA_INGEST_URL, json={{
                    "tracking_id": CLARVIA_TRACKING_ID,
                    "user_agent": ua, "path": path, "method": method,
                }}, timeout=aiohttp.ClientTimeout(total=5))
        except Exception:
            pass  # Non-blocking, best-effort

app.add_middleware(ClarviAgentTracker)'''

    snippet_nodejs = f'''// Add as Express middleware
const AGENT_PATTERNS = {str(AGENT_PATTERNS).replace("'", '"')};
const CLARVIA_TRACKING_ID = "{tracking_id}";
const CLARVIA_INGEST_URL = "{INGEST_URL}";

function clarviaAgentTracker(req, res, next) {{
  const ua = (req.headers["user-agent"] || "").toLowerCase();
  const matched = AGENT_PATTERNS.some(p => ua.includes(p));
  if (matched) {{
    // Non-blocking POST to Clarvia
    fetch(CLARVIA_INGEST_URL, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        tracking_id: CLARVIA_TRACKING_ID,
        user_agent: ua, path: req.path, method: req.method,
      }}),
      signal: AbortSignal.timeout(5000),
    }}).catch(() => {{}});
  }}
  next();
}}

app.use(clarviaAgentTracker);'''

    snippet_go = f'''// Add as Go net/http middleware
package main

import (
\t"bytes"
\t"encoding/json"
\t"net/http"
\t"strings"
\t"time"
)

var agentPatterns = []string{{{", ".join(f'"{p}"' for p in AGENT_PATTERNS)}}}
const clarviaTrackingID = "{tracking_id}"
const clarviaIngestURL = "{INGEST_URL}"

func clarviaAgentTracker(next http.Handler) http.Handler {{
\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {{
\t\tua := strings.ToLower(r.Header.Get("User-Agent"))
\t\tfor _, p := range agentPatterns {{
\t\t\tif strings.Contains(ua, p) {{
\t\t\t\tgo func() {{
\t\t\t\t\tbody, _ := json.Marshal(map[string]string{{
\t\t\t\t\t\t"tracking_id": clarviaTrackingID,
\t\t\t\t\t\t"user_agent": ua, "path": r.URL.Path, "method": r.Method,
\t\t\t\t\t}})
\t\t\t\t\tclient := &http.Client{{Timeout: 5 * time.Second}}
\t\t\t\t\tclient.Post(clarviaIngestURL, "application/json", bytes.NewReader(body))
\t\t\t\t}}()
\t\t\t\tbreak
\t\t\t}}
\t\t}}
\t\tnext.ServeHTTP(w, r)
\t}})
}}'''

    return {
        "python": snippet_python,
        "nodejs": snippet_nodejs,
        "go": snippet_go,
    }
