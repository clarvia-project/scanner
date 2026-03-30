"""Agent traffic measurement — middleware + API endpoints.

Detects AI agent user-agents hitting the Clarvia API and logs them.
Provides aggregate stats and per-tool breakdowns.

Endpoints:
    GET /v1/traffic/stats          — daily agent traffic summary
    GET /v1/traffic/by-tool/{slug} — traffic for a specific tool
"""

import json
import logging
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

router = APIRouter(prefix="/v1/traffic", tags=["traffic"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent detection patterns
# ---------------------------------------------------------------------------

# Mapping: pattern (lowercase) -> canonical agent_type label
AGENT_SIGNATURES: dict[str, str] = {
    "claude-agent": "claude",
    "claudebot": "claude",
    "anthropic": "claude",
    "chatgpt-user": "gpt",
    "gptbot": "gpt",
    "openai": "gpt",
    "cursor": "cursor",
    "perplexitybot": "perplexity",
    "perplexity": "perplexity",
    "copilot": "copilot",
    "github-copilot": "copilot",
    "langchain": "langchain",
    "crewai": "crewai",
    "autogpt": "autogpt",
    "devin": "devin",
    "gemini": "gemini",
    "cohere": "cohere",
    "mistral": "mistral",
}

# Generic bot detection (lower priority — only if no specific match)
# Matches "bot" as a word or as a suffix (e.g., SomeBot, GoogleBot, Bingbot)
GENERIC_BOT_PATTERN = re.compile(r"bot\b", re.IGNORECASE)


def classify_agent(user_agent: str) -> Optional[str]:
    """Classify a user-agent string into an agent type.

    Returns the agent type string or None if not an agent.
    """
    if not user_agent:
        return None
    ua_lower = user_agent.lower()

    # Check specific signatures first
    for pattern, agent_type in AGENT_SIGNATURES.items():
        if pattern in ua_lower:
            return agent_type

    # Generic bot fallback
    if GENERIC_BOT_PATTERN.search(user_agent):
        return "other_bot"

    return None


# ---------------------------------------------------------------------------
# JSONL persistence
# ---------------------------------------------------------------------------

def _traffic_file() -> Path:
    """Find or create the agent-traffic JSONL file."""
    candidates = [
        Path("/app/data/agent-traffic.jsonl"),
    ]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data" / "agent-traffic.jsonl")
        except IndexError:
            break
    for p in candidates:
        if p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
    return candidates[0]


def _extract_tool_slug(path: str) -> Optional[str]:
    """Extract a tool slug from the request path if applicable.

    Matches patterns like:
        /v1/history/{slug}
        /api/scan -> None (no slug)
        /v1/score?url=... -> None (slug in query, not path)
        /v1/traffic/by-tool/{slug}
    """
    # Direct slug in path
    patterns = [
        r"/v1/history/([^/]+)",
        r"/v1/traffic/by-tool/([^/]+)",
        r"/v1/profiles?/([^/]+)",
        r"/v1/badge/([^/]+)",
    ]
    for pat in patterns:
        m = re.search(pat, path)
        if m:
            slug = m.group(1)
            # Skip sub-paths like /delta, /sarif
            if slug not in ("delta", "stats", "by-tool"):
                return slug
    return None


def _log_traffic(entry: dict) -> None:
    """Append a traffic entry to the JSONL log file."""
    try:
        path = _traffic_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug("Failed to write agent traffic log: %s", e)


def _load_traffic(days: int = 7, slug: Optional[str] = None) -> list[dict]:
    """Load traffic entries from the JSONL file."""
    path = _traffic_file()
    if not path.exists():
        return []

    cutoff_ts = time.time() - (days * 86400)
    results = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Filter by age
                    ts = entry.get("timestamp_unix", 0)
                    if ts < cutoff_ts:
                        continue
                    # Filter by slug if specified
                    if slug and entry.get("tool_slug") != slug:
                        continue
                    results.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.debug("Failed to read agent traffic log: %s", e)

    return results


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class AgentTrafficMiddleware(BaseHTTPMiddleware):
    """Detects agent user-agents and logs requests to JSONL.

    Lightweight — only writes a single JSON line per agent request.
    Does not block or slow down the response.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Only log on successful or client-error responses (skip 5xx retries)
        user_agent = request.headers.get("user-agent", "")
        agent_type = classify_agent(user_agent)

        if agent_type:
            path = request.url.path
            tool_slug = _extract_tool_slug(path)
            now = datetime.now(timezone.utc)

            entry = {
                "timestamp": now.isoformat(),
                "timestamp_unix": time.time(),
                "user_agent": user_agent[:300],
                "path": path,
                "tool_slug": tool_slug,
                "agent_type": agent_type,
                "status_code": response.status_code,
                "method": request.method,
            }
            _log_traffic(entry)

        return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/stats")
async def agent_traffic_stats(
    days: int = Query(7, ge=1, le=90),
):
    """Get agent traffic summary — daily counts by agent type.

    Shows how many AI agents are visiting Clarvia, broken down by
    type (Claude, GPT, Cursor, etc.) and day.
    """
    events = _load_traffic(days=days)

    if not events:
        return {
            "period_days": days,
            "total_requests": 0,
            "by_agent_type": {},
            "daily": [],
            "message": "No agent traffic recorded yet.",
        }

    # Aggregate by agent type
    by_type: dict[str, int] = Counter()
    # Aggregate by day
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    # Total
    total = len(events)

    for e in events:
        agent = e.get("agent_type", "unknown")
        by_type[agent] += 1

        ts = e.get("timestamp", "")
        day = ts[:10] if len(ts) >= 10 else "unknown"
        by_day[day][agent] += 1
        by_day[day]["_total"] += 1

    # Format daily breakdown
    daily = []
    for day in sorted(by_day.keys()):
        counts = dict(by_day[day])
        day_total = counts.pop("_total", 0)
        daily.append({
            "date": day,
            "total": day_total,
            "by_agent": counts,
        })

    # Top paths
    path_counter: Counter = Counter()
    for e in events:
        path_counter[e.get("path", "")] += 1

    return {
        "period_days": days,
        "total_requests": total,
        "by_agent_type": dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True)),
        "daily": daily,
        "top_paths": [{"path": p, "count": c} for p, c in path_counter.most_common(15)],
    }


@router.get("/by-tool/{slug}")
async def agent_traffic_by_tool(
    slug: str,
    days: int = Query(7, ge=1, le=90),
):
    """Get agent traffic for a specific tool.

    Shows which agents are accessing data about this tool and how often.
    """
    slug = slug.strip().lower()
    if not slug:
        raise HTTPException(status_code=400, detail="slug is required")

    events = _load_traffic(days=days, slug=slug)

    if not events:
        return {
            "tool_slug": slug,
            "period_days": days,
            "total_requests": 0,
            "by_agent_type": {},
            "daily": [],
            "message": f"No agent traffic for '{slug}' in the last {days} days.",
        }

    by_type: Counter = Counter()
    by_day: dict[str, int] = Counter()

    for e in events:
        by_type[e.get("agent_type", "unknown")] += 1
        ts = e.get("timestamp", "")
        day = ts[:10] if len(ts) >= 10 else "unknown"
        by_day[day] += 1

    daily = [{"date": d, "requests": c} for d, c in sorted(by_day.items())]

    return {
        "tool_slug": slug,
        "period_days": days,
        "total_requests": len(events),
        "by_agent_type": dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True)),
        "daily": daily,
    }
