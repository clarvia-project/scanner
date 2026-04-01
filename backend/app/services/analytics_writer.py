"""Persistent analytics writer for Clarvia API traffic monitoring.

Primary storage: Supabase analytics_events table (survives Render restarts).
Secondary storage: Daily JSONL files in backend/data/analytics/ (local cache).

Both stores are written on every flush. JSONL is used for fast local reads;
Supabase is the durable source of truth that persists across deploys.

Designed to be:
- Async-safe: writes happen in a background task, never blocking request handling
- Dual-store: Supabase (persistent) + JSONL (local cache)
- Query-friendly: each line is a self-contained JSON object with all fields
"""

import asyncio
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Resolve analytics directory relative to backend/data/analytics/
_ANALYTICS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "analytics"
_ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

# Known AI agent user-agent patterns for identification
AGENT_SIGNATURES: dict[str, list[str]] = {
    "Claude": ["claude", "anthropic"],
    "GPT": ["openai", "gpt", "chatgpt"],
    "Cursor": ["cursor"],
    "Copilot": ["copilot", "github-copilot"],
    "Windsurf": ["windsurf"],
    "Cline": ["cline"],
    "Aider": ["aider"],
    "Continue": ["continue"],
    "Bolt": ["bolt"],
    "v0": ["v0"],
    "Devin": ["devin"],
    "Replit": ["replit-agent"],
    "Perplexity": ["perplexity"],
    "Gemini": ["gemini"],
    "Mistral": ["mistral"],
    "Cohere": ["cohere"],
    "LangChain": ["langchain"],
    "CrewAI": ["crewai"],
    "AutoGPT": ["autogpt"],
    "Smithery": ["smithery"],
    "Glama": ["glama"],
    "MCP Client": ["mcp-client"],
    "Zapier": ["zapier"],
    "n8n": ["n8n"],
    "Make": ["make.com"],
    "Composio": ["composio"],
}

# MCP tool endpoint patterns to extract tool names
_MCP_TOOL_PREFIXES = ("/mcp/", "/v1/mcp/")

# Endpoints that indicate tool search/scan activity
_TOOL_ACTIVITY_PATTERNS = {
    "/v1/search": "search",
    "/v1/feed/": "feed",
    "/api/scan": "scan",
    "/v1/score": "score",
    "/v1/leaderboard": "leaderboard",
    "/v1/categories": "categories",
    "/v1/services": "services",
}


def identify_agent(user_agent: str) -> str | None:
    """Identify the AI agent from a user-agent string.

    Returns the canonical agent name (e.g. 'Claude', 'GPT') or None for
    human/bot traffic.
    """
    if not user_agent:
        return None
    ua_lower = user_agent.lower()
    for agent_name, patterns in AGENT_SIGNATURES.items():
        for pattern in patterns:
            if pattern in ua_lower:
                return agent_name
    return None


def classify_tool_activity(path: str, method: str) -> str | None:
    """Classify what kind of tool-related activity this request represents."""
    for prefix, activity in _TOOL_ACTIVITY_PATTERNS.items():
        if path.startswith(prefix):
            return activity
    return None


def classify_referrer(referrer: str) -> str:
    """Classify referrer into a marketing channel."""
    if not referrer:
        return "direct"
    ref = referrer.lower()
    if "smithery.ai" in ref:
        return "smithery"
    if "glama.ai" in ref:
        return "glama"
    if "npmjs.com" in ref or "npm" in ref:
        return "npm"
    if "github.com" in ref:
        return "github"
    if "google" in ref:
        return "google_search"
    if "bing.com" in ref:
        return "bing_search"
    if "pypi.org" in ref:
        return "pypi"
    if "clarvia" in ref:
        return "internal"
    if "twitter.com" in ref or "x.com" in ref:
        return "twitter"
    if "reddit.com" in ref:
        return "reddit"
    if "linkedin.com" in ref:
        return "linkedin"
    return "other"


class AnalyticsWriter:
    """Async JSONL writer that buffers entries and flushes periodically."""

    def __init__(self, flush_interval: float = 5.0, max_buffer: int = 100):
        self._buffer: list[dict[str, Any]] = []
        self._flush_interval = flush_interval
        self._max_buffer = max_buffer
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        """Start the background flush loop."""
        if not self._running:
            self._running = True
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("Analytics writer started (dir=%s)", _ANALYTICS_DIR)

    async def stop(self) -> None:
        """Stop the flush loop and flush remaining buffer."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush()

    async def record(self, entry: dict[str, Any]) -> None:
        """Add an analytics entry to the buffer (non-blocking)."""
        async with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= self._max_buffer:
                await self._flush_unlocked()

    async def _flush_loop(self) -> None:
        """Periodically flush buffer to disk."""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self._flush()

    async def _flush(self) -> None:
        async with self._lock:
            await self._flush_unlocked()

    async def _flush_unlocked(self) -> None:
        """Write buffered entries to JSONL files and Supabase."""
        if not self._buffer:
            return

        # Snapshot and clear buffer
        entries = list(self._buffer)
        self._buffer.clear()

        # Group by date for JSONL file writes
        by_date: dict[str, list[str]] = defaultdict(list)
        for entry in entries:
            day = entry.get("date", date.today().isoformat())
            by_date[day].append(json.dumps(entry, separators=(",", ":"), ensure_ascii=False))

        # Write to local JSONL files (fast local reads)
        loop = asyncio.get_running_loop()
        for day, lines in by_date.items():
            filepath = _ANALYTICS_DIR / f"analytics-{day}.jsonl"
            content = "\n".join(lines) + "\n"
            await loop.run_in_executor(None, self._append_file, filepath, content)

        # Write to Supabase (persistent across restarts)
        await self._flush_to_supabase(entries)

    async def _flush_to_supabase(self, entries: list[dict[str, Any]]) -> None:
        """Batch insert analytics entries into Supabase analytics_events table."""
        try:
            from .supabase_client import get_supabase
            client = get_supabase()
            if not client:
                return  # Supabase not configured — JSONL only

            rows = [
                {
                    "ts": entry["ts"],
                    "date": entry["date"],
                    "hour": entry.get("hour", "00"),
                    "endpoint": entry.get("endpoint", ""),
                    "method": entry.get("method", "GET"),
                    "status": entry.get("status", 200),
                    "response_ms": entry.get("response_ms", 0),
                    "ip_hash": entry.get("ip_hash", ""),
                    "ua": entry.get("ua", "")[:200],
                    "agent": entry.get("agent"),
                    "tool_activity": entry.get("tool_activity"),
                    "referrer": entry.get("referrer"),
                    "referrer_channel": entry.get("referrer_channel"),
                    "utm_source": entry.get("utm_source"),
                    "utm_medium": entry.get("utm_medium"),
                    "utm_campaign": entry.get("utm_campaign"),
                }
                for entry in entries
            ]

            # Batch insert (Supabase handles up to 1000 rows per call)
            for i in range(0, len(rows), 500):
                batch = rows[i : i + 500]
                client.table("analytics_events").insert(batch).execute()

        except Exception as e:
            # Never let Supabase errors kill the analytics pipeline
            logger.warning("Supabase analytics flush failed (JSONL still written): %s", e)

    @staticmethod
    def _append_file(filepath: Path, content: str) -> None:
        """Append content to file (sync, runs in executor)."""
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            logger.error("Failed to write analytics to %s: %s", filepath, e)


def build_analytics_entry(
    path: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    client_ip: str,
    user_agent: str,
    referrer: str = "",
    query_string: str = "",
) -> dict[str, Any]:
    """Build a structured analytics entry from request data."""
    now = datetime.now(timezone.utc)
    agent_name = identify_agent(user_agent)
    tool_activity = classify_tool_activity(path, method)

    entry: dict[str, Any] = {
        "ts": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.strftime("%H"),
        "endpoint": path,
        "method": method,
        "status": status_code,
        "response_ms": round(response_time_ms, 1),
        "ip_hash": hex(hash(client_ip) & 0xFFFFFFFF),  # privacy-safe hash
        "ua": user_agent[:200] if user_agent else "",
    }

    if agent_name:
        entry["agent"] = agent_name

    if tool_activity:
        entry["tool_activity"] = tool_activity

    # Extract query param for search tracking
    if path.startswith("/v1/search") and "?" in path:
        # Path won't have query string; caller should pass it separately
        pass

    # Attribution tracking
    if referrer:
        entry["referrer"] = referrer[:500]
        entry["referrer_channel"] = classify_referrer(referrer)

    # UTM parameters
    if query_string:
        from urllib.parse import parse_qs
        params = parse_qs(query_string)
        utm_source = params.get("utm_source", [None])[0]
        utm_medium = params.get("utm_medium", [None])[0]
        utm_campaign = params.get("utm_campaign", [None])[0]
        if utm_source:
            entry["utm_source"] = utm_source[:100]
        if utm_medium:
            entry["utm_medium"] = utm_medium[:100]
        if utm_campaign:
            entry["utm_campaign"] = utm_campaign[:100]

    return entry


# ---------------------------------------------------------------------------
# JSONL reader utilities for analytics API
# ---------------------------------------------------------------------------

def _iter_jsonl(filepath: Path):
    """Yield parsed JSON objects from a JSONL file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        return


def _get_date_range_files(days: int = 7) -> list[Path]:
    """Get JSONL files for the last N days."""
    files = []
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        fp = _ANALYTICS_DIR / f"analytics-{d.isoformat()}.jsonl"
        if fp.exists():
            files.append(fp)
    return files


def get_summary(days: int = 7) -> dict[str, Any]:
    """Compute analytics summary over the last N days.

    Returns daily/weekly/monthly aggregates of requests, agents, endpoints.
    """
    files = _get_date_range_files(days)

    total_requests = 0
    total_agent_requests = 0
    total_errors = 0
    response_times: list[float] = []
    daily_counts: Counter = Counter()
    daily_agent_counts: Counter = Counter()
    status_counts: Counter = Counter()
    agent_counts: Counter = Counter()
    endpoint_counts: Counter = Counter()
    method_counts: Counter = Counter()
    tool_activity_counts: Counter = Counter()
    unique_ips: set[str] = set()
    hourly_distribution: Counter = Counter()

    for fp in files:
        for entry in _iter_jsonl(fp):
            total_requests += 1
            day = entry.get("date", "")
            daily_counts[day] += 1
            status_counts[entry.get("status", 0)] += 1
            endpoint_counts[entry.get("endpoint", "")] += 1
            method_counts[entry.get("method", "")] += 1
            hourly_distribution[entry.get("hour", "00")] += 1

            if entry.get("ip_hash"):
                unique_ips.add(entry["ip_hash"])

            rt = entry.get("response_ms")
            if rt is not None:
                response_times.append(rt)

            if entry.get("status", 200) >= 400:
                total_errors += 1

            agent = entry.get("agent")
            if agent:
                total_agent_requests += 1
                agent_counts[agent] += 1
                daily_agent_counts[day] += 1

            ta = entry.get("tool_activity")
            if ta:
                tool_activity_counts[ta] += 1

    avg_response = round(sum(response_times) / len(response_times), 1) if response_times else 0
    p95_idx = int(len(response_times) * 0.95)
    p95_response = round(sorted(response_times)[p95_idx], 1) if len(response_times) > 20 else 0

    return {
        "period_days": days,
        "total_requests": total_requests,
        "total_agent_requests": total_agent_requests,
        "agent_ratio_pct": round(total_agent_requests / max(total_requests, 1) * 100, 1),
        "unique_visitors": len(unique_ips),
        "total_errors": total_errors,
        "error_rate_pct": round(total_errors / max(total_requests, 1) * 100, 2),
        "avg_response_ms": avg_response,
        "p95_response_ms": p95_response,
        "daily": sorted(
            [{"date": d, "requests": c, "agent_requests": daily_agent_counts.get(d, 0)}
             for d, c in daily_counts.items()],
            key=lambda x: x["date"],
        ),
        "by_status": dict(status_counts.most_common(10)),
        "by_method": dict(method_counts.most_common()),
        "peak_hours": [
            {"hour": h, "requests": c}
            for h, c in hourly_distribution.most_common(24)
        ],
        "tool_activity": dict(tool_activity_counts.most_common()),
    }


def get_agent_breakdown(days: int = 7) -> dict[str, Any]:
    """Get detailed agent breakdown over the last N days."""
    files = _get_date_range_files(days)

    agent_counts: Counter = Counter()
    agent_daily: dict[str, Counter] = defaultdict(Counter)
    agent_endpoints: dict[str, Counter] = defaultdict(Counter)
    agent_response_times: dict[str, list[float]] = defaultdict(list)
    total = 0
    agent_total = 0

    for fp in files:
        for entry in _iter_jsonl(fp):
            total += 1
            agent = entry.get("agent")
            if agent:
                agent_total += 1
                agent_counts[agent] += 1
                agent_daily[agent][entry.get("date", "")] += 1
                agent_endpoints[agent][entry.get("endpoint", "")] += 1
                rt = entry.get("response_ms")
                if rt is not None:
                    agent_response_times[agent].append(rt)

    agents = []
    for name, count in agent_counts.most_common(30):
        rts = agent_response_times.get(name, [])
        agents.append({
            "name": name,
            "requests": count,
            "pct_of_total": round(count / max(total, 1) * 100, 1),
            "pct_of_agents": round(count / max(agent_total, 1) * 100, 1),
            "avg_response_ms": round(sum(rts) / len(rts), 1) if rts else 0,
            "top_endpoints": [
                {"endpoint": ep, "count": c}
                for ep, c in agent_endpoints[name].most_common(5)
            ],
            "daily_trend": sorted(
                [{"date": d, "count": c} for d, c in agent_daily[name].items()],
                key=lambda x: x["date"],
            ),
        })

    return {
        "period_days": days,
        "total_requests": total,
        "agent_requests": agent_total,
        "agent_ratio_pct": round(agent_total / max(total, 1) * 100, 1),
        "unique_agents": len(agent_counts),
        "agents": agents,
    }


def get_endpoint_breakdown(days: int = 7) -> dict[str, Any]:
    """Get endpoint usage breakdown over the last N days."""
    files = _get_date_range_files(days)

    endpoint_counts: Counter = Counter()
    endpoint_methods: dict[str, Counter] = defaultdict(Counter)
    endpoint_statuses: dict[str, Counter] = defaultdict(Counter)
    endpoint_agents: dict[str, Counter] = defaultdict(Counter)
    endpoint_response_times: dict[str, list[float]] = defaultdict(list)

    for fp in files:
        for entry in _iter_jsonl(fp):
            ep = entry.get("endpoint", "")
            endpoint_counts[ep] += 1
            endpoint_methods[ep][entry.get("method", "")] += 1
            endpoint_statuses[ep][entry.get("status", 0)] += 1
            agent = entry.get("agent")
            if agent:
                endpoint_agents[ep][agent] += 1
            rt = entry.get("response_ms")
            if rt is not None:
                endpoint_response_times[ep].append(rt)

    endpoints = []
    for ep, count in endpoint_counts.most_common(50):
        rts = endpoint_response_times.get(ep, [])
        errors = sum(c for s, c in endpoint_statuses[ep].items() if s >= 400)
        endpoints.append({
            "endpoint": ep,
            "requests": count,
            "methods": dict(endpoint_methods[ep]),
            "error_count": errors,
            "error_rate_pct": round(errors / max(count, 1) * 100, 1),
            "avg_response_ms": round(sum(rts) / len(rts), 1) if rts else 0,
            "top_agents": [
                {"agent": a, "count": c}
                for a, c in endpoint_agents[ep].most_common(5)
            ],
        })

    return {
        "period_days": days,
        "total_endpoints": len(endpoint_counts),
        "endpoints": endpoints,
    }


def get_tool_activity(days: int = 7) -> dict[str, Any]:
    """Get tool search/scan activity breakdown over the last N days."""
    files = _get_date_range_files(days)

    activity_counts: Counter = Counter()
    activity_daily: dict[str, Counter] = defaultdict(Counter)
    activity_agents: dict[str, Counter] = defaultdict(Counter)
    search_endpoints: Counter = Counter()
    scan_endpoints: Counter = Counter()

    for fp in files:
        for entry in _iter_jsonl(fp):
            ta = entry.get("tool_activity")
            if not ta:
                continue
            activity_counts[ta] += 1
            activity_daily[ta][entry.get("date", "")] += 1
            agent = entry.get("agent")
            if agent:
                activity_agents[ta][agent] += 1

            ep = entry.get("endpoint", "")
            if ta == "search":
                search_endpoints[ep] += 1
            elif ta == "scan":
                scan_endpoints[ep] += 1

    activities = []
    for activity, count in activity_counts.most_common():
        activities.append({
            "activity": activity,
            "total": count,
            "daily_trend": sorted(
                [{"date": d, "count": c} for d, c in activity_daily[activity].items()],
                key=lambda x: x["date"],
            ),
            "by_agent": [
                {"agent": a, "count": c}
                for a, c in activity_agents[activity].most_common(10)
            ],
        })

    return {
        "period_days": days,
        "activities": activities,
        "total_tool_requests": sum(activity_counts.values()),
    }


# Singleton writer instance
analytics_writer = AnalyticsWriter()
