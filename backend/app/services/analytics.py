"""In-memory analytics collector for Clarvia KPI dashboard.

Tracks:
- API requests by endpoint, method, status code
- Agent vs human traffic (User-Agent detection)
- Scan usage (count, unique URLs)
- MCP tool calls
- Geographic distribution (from IP, best-effort)
- Hourly/daily aggregation

All data is in-memory with periodic Supabase persistence (if configured).
Designed to be lightweight — no external dependencies required.
"""

import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

# Known AI agent user-agent patterns (expanded)
AGENT_PATTERNS = [
    "claude", "anthropic", "openai", "gpt", "chatgpt",
    "cursor", "copilot", "github-copilot",
    "perplexity", "langchain", "autogpt", "babyagi",
    "crewai", "browserbase", "playwright-agent",
    "semantic-kernel", "cohere", "mistral", "gemini",
    "devin", "windsurf", "cline", "aider", "continue",
    "bolt", "v0", "replit-agent", "mcp-client",
    "smithery", "glama", "zapier", "make.com",
    "n8n", "activepieces", "composio",
]

# Bot patterns (not agents, just crawlers)
BOT_PATTERNS = [
    "googlebot", "bingbot", "yandexbot", "baiduspider",
    "duckduckbot", "slurp", "facebot", "twitterbot",
    "linkedinbot", "applebot", "semrushbot", "ahrefsbot",
    "mj12bot", "dotbot", "petalbot",
]


class AnalyticsCollector:
    """Lightweight in-memory analytics for KPI tracking."""

    def __init__(self) -> None:
        self._start_time = time.time()

        # Request counters
        self._total_requests = 0
        self._requests_by_endpoint: Counter = Counter()
        self._requests_by_method: Counter = Counter()
        self._requests_by_status: Counter = Counter()

        # Visitor tracking — use counter instead of unbounded set to save memory
        self._unique_ip_count: int = 0
        self._recent_ips: set[str] = set()  # Capped at 10k, then roll over
        self._agent_requests = 0
        self._human_requests = 0
        self._bot_requests = 0
        self._agent_breakdown: Counter = Counter()  # agent_name -> count

        # Scan tracking
        self._scans_total = 0
        self._scans_unique_url_count: int = 0
        self._recent_scan_urls: set[str] = set()  # Capped at 5k
        self._scans_by_hour: dict[str, int] = defaultdict(int)

        # MCP tracking
        self._mcp_calls = 0
        self._mcp_tool_calls: Counter = Counter()  # tool_name -> count

        # API endpoint usage
        self._api_calls: Counter = Counter()  # endpoint -> count

        # Hourly buckets (last 72 hours)
        self._hourly_requests: dict[str, int] = defaultdict(int)
        self._hourly_agents: dict[str, int] = defaultdict(int)
        self._hourly_scans: dict[str, int] = defaultdict(int)

        # Daily buckets (last 30 days)
        self._daily_requests: dict[str, int] = defaultdict(int)
        self._daily_agents: dict[str, int] = defaultdict(int)
        self._daily_scans: dict[str, int] = defaultdict(int)
        self._daily_unique_ips: dict[str, set] = defaultdict(set)

        # Error tracking
        self._errors: list[dict[str, Any]] = []  # last 100 errors
        self._error_count = 0

        # Response time tracking
        self._response_times: list[float] = []  # last 1000

    def _hour_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")

    def _day_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def detect_visitor_type(self, user_agent: str) -> tuple[str, str | None]:
        """Classify visitor as agent/bot/human. Returns (type, agent_name)."""
        if not user_agent:
            return "human", None
        ua_lower = user_agent.lower()

        for pattern in AGENT_PATTERNS:
            if pattern in ua_lower:
                return "agent", pattern

        for pattern in BOT_PATTERNS:
            if pattern in ua_lower:
                return "bot", pattern

        return "human", None

    def record_request(
        self,
        path: str,
        method: str,
        status_code: int,
        client_ip: str,
        user_agent: str,
        response_time_ms: float | None = None,
    ) -> None:
        """Record a single HTTP request."""
        self._total_requests += 1
        self._requests_by_endpoint[path] += 1
        self._requests_by_method[method] += 1
        self._requests_by_status[status_code] += 1

        # Visitor type
        visitor_type, agent_name = self.detect_visitor_type(user_agent)
        if visitor_type == "agent":
            self._agent_requests += 1
            if agent_name:
                self._agent_breakdown[agent_name] += 1
        elif visitor_type == "bot":
            self._bot_requests += 1
        else:
            self._human_requests += 1

        # Unique IPs — capped rolling set
        if client_ip not in self._recent_ips:
            self._unique_ip_count += 1
            self._recent_ips.add(client_ip)
            if len(self._recent_ips) > 10_000:
                self._recent_ips.clear()  # Roll over to prevent unbounded growth

        # Time buckets
        hour = self._hour_key()
        day = self._day_key()
        self._hourly_requests[hour] += 1
        self._daily_requests[day] += 1
        daily_ips = self._daily_unique_ips[day]
        if len(daily_ips) < 5_000:  # Cap per-day IP set to prevent memory bloat
            daily_ips.add(client_ip)

        if visitor_type == "agent":
            self._hourly_agents[hour] += 1
            self._daily_agents[day] += 1

        # Response time
        if response_time_ms is not None:
            self._response_times.append(response_time_ms)
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-1000:]

        # Error tracking
        if status_code >= 400:
            self._error_count += 1
            self._errors.append({
                "path": path,
                "method": method,
                "status": status_code,
                "ip": client_ip[:8] + "***",  # partial IP for privacy
                "agent": agent_name,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            if len(self._errors) > 100:
                self._errors = self._errors[-100:]

        # API usage tracking
        if path.startswith("/v1/") or path.startswith("/api/"):
            self._api_calls[path] += 1

    def record_scan(self, url: str) -> None:
        """Record a scan event."""
        self._scans_total += 1
        if url not in self._recent_scan_urls:
            self._scans_unique_url_count += 1
            self._recent_scan_urls.add(url)
            if len(self._recent_scan_urls) > 5_000:
                self._recent_scan_urls.clear()
        hour = self._hour_key()
        day = self._day_key()
        self._hourly_scans[hour] += 1
        self._daily_scans[day] += 1

    def record_mcp_call(self, tool_name: str) -> None:
        """Record an MCP tool call."""
        self._mcp_calls += 1
        self._mcp_tool_calls[tool_name] += 1

    def _cleanup_old_buckets(self) -> None:
        """Remove hourly buckets older than 72h, daily older than 30d."""
        now = datetime.now(timezone.utc)
        # Keep last 72 hours
        cutoff_hour = (now.timestamp() - 72 * 3600)
        for key in list(self._hourly_requests.keys()):
            try:
                dt = datetime.strptime(key, "%Y-%m-%d-%H").replace(tzinfo=timezone.utc)
                if dt.timestamp() < cutoff_hour:
                    self._hourly_requests.pop(key, None)
                    self._hourly_agents.pop(key, None)
                    self._hourly_scans.pop(key, None)
            except ValueError:
                pass

        # Keep last 30 days
        cutoff_day = (now.timestamp() - 30 * 86400)
        for key in list(self._daily_requests.keys()):
            try:
                dt = datetime.strptime(key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if dt.timestamp() < cutoff_day:
                    self._daily_requests.pop(key, None)
                    self._daily_agents.pop(key, None)
                    self._daily_scans.pop(key, None)
                    self._daily_unique_ips.pop(key, None)
            except ValueError:
                pass

    def get_kpi(self) -> dict[str, Any]:
        """Return full KPI snapshot for admin dashboard."""
        self._cleanup_old_buckets()

        uptime_s = int(time.time() - self._start_time)
        avg_response = (
            round(sum(self._response_times) / len(self._response_times), 1)
            if self._response_times else 0
        )
        p95_response = (
            round(sorted(self._response_times)[int(len(self._response_times) * 0.95)], 1)
            if len(self._response_times) > 20 else 0
        )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime_s,

            # Traffic overview
            "traffic": {
                "total_requests": self._total_requests,
                "unique_visitors": self._unique_ip_count,
                "agent_requests": self._agent_requests,
                "human_requests": self._human_requests,
                "bot_requests": self._bot_requests,
                "agent_ratio": round(
                    self._agent_requests / max(self._total_requests, 1) * 100, 1
                ),
            },

            # Agent breakdown
            "agents": {
                "breakdown": [
                    {"name": name, "requests": count}
                    for name, count in self._agent_breakdown.most_common(20)
                ],
                "unique_agents": len(self._agent_breakdown),
            },

            # Scan metrics
            "scans": {
                "total": self._scans_total,
                "unique_urls": self._scans_unique_url_count,
            },

            # MCP metrics
            "mcp": {
                "total_calls": self._mcp_calls,
                "by_tool": [
                    {"tool": name, "calls": count}
                    for name, count in self._mcp_tool_calls.most_common(15)
                ],
            },

            # API usage
            "api_usage": {
                "top_endpoints": [
                    {"endpoint": ep, "calls": count}
                    for ep, count in self._api_calls.most_common(20)
                ],
            },

            # Performance
            "performance": {
                "avg_response_ms": avg_response,
                "p95_response_ms": p95_response,
                "error_count": self._error_count,
                "error_rate": round(
                    self._error_count / max(self._total_requests, 1) * 100, 2
                ),
                "by_status": dict(self._requests_by_status.most_common(10)),
            },

            # Time series (hourly, last 72h)
            "hourly": {
                "requests": sorted(
                    [{"hour": k, "count": v} for k, v in self._hourly_requests.items()],
                    key=lambda x: x["hour"],
                )[-72:],
                "agents": sorted(
                    [{"hour": k, "count": v} for k, v in self._hourly_agents.items()],
                    key=lambda x: x["hour"],
                )[-72:],
                "scans": sorted(
                    [{"hour": k, "count": v} for k, v in self._hourly_scans.items()],
                    key=lambda x: x["hour"],
                )[-72:],
            },

            # Time series (daily, last 30d)
            "daily": {
                "requests": sorted(
                    [{"date": k, "count": v} for k, v in self._daily_requests.items()],
                    key=lambda x: x["date"],
                )[-30:],
                "agents": sorted(
                    [{"date": k, "count": v} for k, v in self._daily_agents.items()],
                    key=lambda x: x["date"],
                )[-30:],
                "scans": sorted(
                    [{"date": k, "count": v} for k, v in self._daily_scans.items()],
                    key=lambda x: x["date"],
                )[-30:],
                "unique_visitors": sorted(
                    [{"date": k, "count": len(v)} for k, v in self._daily_unique_ips.items()],
                    key=lambda x: x["date"],
                )[-30:],
            },

            # Recent errors
            "recent_errors": self._errors[-20:],
        }


# Singleton instance
analytics = AnalyticsCollector()
