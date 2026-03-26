#!/usr/bin/env python3
"""Clarvia Circuit Breaker — Graceful Degradation System.

Implements per-source circuit breakers so that when external APIs fail,
Clarvia degrades gracefully instead of crashing.

States:
  CLOSED   — Normal operation, requests flow through.
  OPEN     — Source is broken, skip requests, serve cached data.
  HALF_OPEN — Cooldown expired, try a single probe request.

Thresholds:
  - 3 consecutive failures  → OPEN
  - 30 min cooldown         → HALF_OPEN
  - 1 success in HALF_OPEN  → CLOSED
  - 1 failure in HALF_OPEN  → OPEN (reset cooldown)

Usage:
    from circuit_breaker import CircuitBreaker, get_breaker

    breaker = get_breaker("github")
    if breaker.allow_request():
        try:
            result = call_github_api()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
    else:
        # Use cached data
        result = load_cached_response("github")
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CB_DIR = DATA_DIR / "circuit_breaker"
STATE_PATH = CB_DIR / "state.json"
CACHE_DIR = CB_DIR / "cache"

sys.path.insert(0, str(SCRIPT_DIR.parent))

# ---------------------------------------------------------------------------
# Circuit breaker constants
# ---------------------------------------------------------------------------

FAILURE_THRESHOLD = 3
COOLDOWN_SECONDS = 1800  # 30 minutes
SLOW_RESPONSE_THRESHOLD = 5.0  # seconds


class CBState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Persistent state management
# ---------------------------------------------------------------------------

def _load_all_states() -> dict[str, dict]:
    """Load all circuit breaker states from disk."""
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Corrupt circuit breaker state file, resetting")
    return {}


def _save_all_states(states: dict[str, dict]) -> None:
    """Persist all circuit breaker states to disk."""
    CB_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(states, f, indent=2, default=str)
    tmp.replace(STATE_PATH)


# ---------------------------------------------------------------------------
# CircuitBreaker class
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Per-source circuit breaker with persistent state."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = FAILURE_THRESHOLD,
        cooldown_seconds: int = COOLDOWN_SECONDS,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        # Load persisted state
        states = _load_all_states()
        saved = states.get(name, {})

        self.state = CBState(saved.get("state", CBState.CLOSED.value))
        self.failure_count = saved.get("failure_count", 0)
        self.last_failure_time = saved.get("last_failure_time", 0.0)
        self.last_success_time = saved.get("last_success_time", 0.0)
        self.opened_at = saved.get("opened_at", 0.0)
        self.total_failures = saved.get("total_failures", 0)
        self.total_successes = saved.get("total_successes", 0)
        self.total_rejected = saved.get("total_rejected", 0)

    def _persist(self) -> None:
        """Save current state to disk."""
        states = _load_all_states()
        states[self.name] = {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "opened_at": self.opened_at,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "total_rejected": self.total_rejected,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_all_states(states)

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Returns:
            True if the request can proceed, False if it should be rejected.
        """
        if self.state == CBState.CLOSED:
            return True

        if self.state == CBState.OPEN:
            # Check if cooldown has elapsed
            elapsed = time.time() - self.opened_at
            if elapsed >= self.cooldown_seconds:
                logger.info(
                    "Circuit breaker [%s]: OPEN -> HALF_OPEN (cooldown %.0fs elapsed)",
                    self.name, elapsed,
                )
                self.state = CBState.HALF_OPEN
                self._persist()
                return True  # Allow one probe request
            else:
                self.total_rejected += 1
                return False

        if self.state == CBState.HALF_OPEN:
            # In HALF_OPEN, allow exactly one probe
            return True

        return False

    def record_success(self) -> None:
        """Record a successful request."""
        self.total_successes += 1
        self.failure_count = 0
        self.last_success_time = time.time()

        if self.state in (CBState.OPEN, CBState.HALF_OPEN):
            logger.info(
                "Circuit breaker [%s]: %s -> CLOSED (success)",
                self.name, self.state.value.upper(),
            )
            self.state = CBState.CLOSED

        self._persist()

    def record_failure(self, error: str = "") -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()

        if self.state == CBState.HALF_OPEN:
            # Probe failed — back to OPEN
            logger.warning(
                "Circuit breaker [%s]: HALF_OPEN -> OPEN (probe failed: %s)",
                self.name, error[:100],
            )
            self.state = CBState.OPEN
            self.opened_at = time.time()

        elif self.state == CBState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.warning(
                    "Circuit breaker [%s]: CLOSED -> OPEN (%d consecutive failures)",
                    self.name, self.failure_count,
                )
                self.state = CBState.OPEN
                self.opened_at = time.time()

        self._persist()

    def force_open(self, reason: str = "") -> None:
        """Manually trip the circuit breaker."""
        logger.warning(
            "Circuit breaker [%s]: forced OPEN — %s", self.name, reason,
        )
        self.state = CBState.OPEN
        self.opened_at = time.time()
        self._persist()

    def force_close(self) -> None:
        """Manually reset the circuit breaker."""
        logger.info("Circuit breaker [%s]: forced CLOSED", self.name)
        self.state = CBState.CLOSED
        self.failure_count = 0
        self._persist()

    def get_status(self) -> dict[str, Any]:
        """Return current status as a dict."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "opened_at": self.opened_at,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "total_rejected": self.total_rejected,
        }


# ---------------------------------------------------------------------------
# Global breaker registry
# ---------------------------------------------------------------------------

_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    """Get or create a named circuit breaker (singleton per name)."""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name, **kwargs)
    return _breakers[name]


# Default breakers for Clarvia sources
SOURCE_NAMES = ["github", "npm", "pypi", "mcp_registry", "clarvia_api"]


def get_all_statuses() -> list[dict[str, Any]]:
    """Return status of all known circuit breakers."""
    statuses = []
    for name in SOURCE_NAMES:
        breaker = get_breaker(name)
        statuses.append(breaker.get_status())
    return statuses


# ---------------------------------------------------------------------------
# Response cache for fallback
# ---------------------------------------------------------------------------

def cache_response(endpoint: str, data: Any) -> None:
    """Cache an API response for fallback serving."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = endpoint.replace("/", "_").replace(":", "_").strip("_")
    cache_path = CACHE_DIR / f"{safe_name}.json"
    cache_entry = {
        "endpoint": endpoint,
        "data": data,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_entry, f, indent=2, default=str)


def load_cached_response(endpoint: str) -> Optional[dict]:
    """Load a cached API response for fallback."""
    safe_name = endpoint.replace("/", "_").replace(":", "_").strip("_")
    cache_path = CACHE_DIR / f"{safe_name}.json"
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Scan retry queue
# ---------------------------------------------------------------------------

RETRY_QUEUE_PATH = CB_DIR / "retry_queue.json"


def queue_scan_retry(url: str, attempt: int = 1) -> None:
    """Queue a failed scan for retry with exponential backoff."""
    CB_DIR.mkdir(parents=True, exist_ok=True)

    queue = []
    if RETRY_QUEUE_PATH.exists():
        try:
            with open(RETRY_QUEUE_PATH, "r") as f:
                queue = json.load(f)
        except (json.JSONDecodeError, ValueError):
            queue = []

    # Max 3 attempts
    if attempt > 3:
        logger.warning("Scan retry exhausted for %s (attempt %d)", url, attempt)
        return

    backoff = min(300 * (2 ** (attempt - 1)), 3600)  # 5min, 10min, 20min (cap 1hr)
    retry_at = time.time() + backoff

    queue.append({
        "url": url,
        "attempt": attempt,
        "retry_at": retry_at,
        "retry_at_iso": datetime.fromtimestamp(retry_at, tz=timezone.utc).isoformat(),
        "queued_at": datetime.now(timezone.utc).isoformat(),
    })

    with open(RETRY_QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2, default=str)

    logger.info(
        "Queued scan retry for %s (attempt %d, backoff %ds)",
        url, attempt, backoff,
    )


def get_pending_retries() -> list[dict]:
    """Get retries that are due now."""
    if not RETRY_QUEUE_PATH.exists():
        return []

    try:
        with open(RETRY_QUEUE_PATH, "r") as f:
            queue = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []

    now = time.time()
    due = [r for r in queue if r.get("retry_at", 0) <= now]
    remaining = [r for r in queue if r.get("retry_at", 0) > now]

    # Write back remaining
    with open(RETRY_QUEUE_PATH, "w") as f:
        json.dump(remaining, f, indent=2, default=str)

    return due


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Print current circuit breaker status."""
    import argparse

    parser = argparse.ArgumentParser(description="Clarvia Circuit Breaker status")
    parser.add_argument("--reset", type=str, help="Reset a specific breaker to CLOSED")
    parser.add_argument("--trip", type=str, help="Force-trip a specific breaker to OPEN")
    args = parser.parse_args()

    if args.reset:
        breaker = get_breaker(args.reset)
        breaker.force_close()
        print(f"Circuit breaker '{args.reset}' reset to CLOSED")
        return

    if args.trip:
        breaker = get_breaker(args.trip)
        breaker.force_open("Manual trip via CLI")
        print(f"Circuit breaker '{args.trip}' forced OPEN")
        return

    statuses = get_all_statuses()
    print(json.dumps(statuses, indent=2, default=str))


if __name__ == "__main__":
    main()
