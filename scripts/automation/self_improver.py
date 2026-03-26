#!/usr/bin/env python3
"""Clarvia Self-Improvement Engine.

Applies Clarvia's own AEO scoring criteria against itself to identify
improvement areas. Generates actionable suggestions and tracks score
progression over time.

Self-assessment dimensions:
  1. API Discoverability — OpenAPI spec availability and validity
  2. Response Format — Consistent JSON across all endpoints
  3. Error Handling — Proper error responses for invalid requests
  4. Documentation — API doc completeness and accuracy
  5. Performance — Average response time across endpoints
  6. Availability — Uptime from healthcheck logs

Usage:
  python scripts/automation/self_improver.py
  python scripts/automation/self_improver.py --dry-run
  python scripts/automation/self_improver.py --api-url http://localhost:8000
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SELF_IMPROVEMENT_DIR = DATA_DIR / "self-improvement"
SELF_IMPROVEMENT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SCRIPT_DIR.parent))
from telegram_notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_API_URL = os.environ.get(
    "CLARVIA_API_URL", "https://clarvia-api.onrender.com"
)
DEFAULT_FRONTEND_URL = os.environ.get(
    "CLARVIA_FRONTEND_URL", "https://clarvia.art"
)

# Endpoints to probe for self-assessment
PROBE_ENDPOINTS = [
    {"path": "/health", "method": "GET", "expect_json": True},
    {"path": "/openapi.json", "method": "GET", "expect_json": True},
    {"path": "/docs", "method": "GET", "expect_json": False},
    {"path": "/api/v1/scan", "method": "POST", "expect_json": True},
    {"path": "/api/v1/index", "method": "GET", "expect_json": True},
    {"path": "/api/v1/trending", "method": "GET", "expect_json": True},
    {"path": "/api/v1/feed/new", "method": "GET", "expect_json": True},
    {"path": "/api/v1/recommend", "method": "GET", "expect_json": True},
]

# Invalid requests to test error handling
ERROR_PROBES = [
    {"path": "/api/v1/scan", "method": "POST", "body": {}, "desc": "empty body"},
    {"path": "/api/v1/scan", "method": "POST", "body": {"url": ""}, "desc": "empty url"},
    {"path": "/api/v1/nonexistent", "method": "GET", "body": None, "desc": "404 route"},
    {"path": "/api/v1/scan", "method": "GET", "body": None, "desc": "wrong method"},
]


# ---------------------------------------------------------------------------
# Assessment functions
# ---------------------------------------------------------------------------

def assess_api_discoverability(api_url: str, timeout: float = 15) -> dict[str, Any]:
    """Check if /openapi.json exists and is valid OpenAPI.

    Scoring (0-10):
      - /openapi.json reachable: 4 pts
      - Valid JSON with 'openapi' version field: 2 pts
      - Has 'paths' with >= 5 routes: 2 pts
      - Has 'info.description': 1 pt
      - Has 'servers' section: 1 pt
    """
    score = 0
    findings: list[str] = []
    evidence: dict[str, Any] = {}

    try:
        resp = requests.get(f"{api_url}/openapi.json", timeout=timeout)
        evidence["status_code"] = resp.status_code

        if resp.status_code == 200:
            score += 4
            findings.append("OpenAPI spec is reachable")
            try:
                spec = resp.json()
                evidence["openapi_version"] = spec.get("openapi", "missing")

                if "openapi" in spec:
                    score += 2
                    findings.append(f"Valid OpenAPI version: {spec['openapi']}")

                paths = spec.get("paths", {})
                evidence["route_count"] = len(paths)
                if len(paths) >= 5:
                    score += 2
                    findings.append(f"{len(paths)} routes documented")
                else:
                    findings.append(f"Only {len(paths)} routes (need >= 5)")

                info = spec.get("info", {})
                if info.get("description"):
                    score += 1
                    findings.append("API description present")
                else:
                    findings.append("Missing API description in info")

                if spec.get("servers"):
                    score += 1
                    findings.append("Server URLs documented")
                else:
                    findings.append("Missing servers section")

            except (json.JSONDecodeError, ValueError):
                findings.append("OpenAPI spec is not valid JSON")
        else:
            findings.append(f"OpenAPI spec returned {resp.status_code}")

    except requests.RequestException as exc:
        findings.append(f"Failed to reach OpenAPI spec: {exc}")
        evidence["error"] = str(exc)

    return {
        "score": score,
        "max": 10,
        "findings": findings,
        "evidence": evidence,
    }


def assess_response_format(api_url: str, timeout: float = 15) -> dict[str, Any]:
    """Check if all JSON endpoints return consistent JSON responses.

    Scoring (0-10):
      - Each JSON endpoint returning valid JSON with correct Content-Type: +1.25 pts
      - All responses have consistent error envelope: +2 pts
    """
    score = 0.0
    findings: list[str] = []
    evidence: dict[str, Any] = {"endpoints": {}}
    json_endpoints = [e for e in PROBE_ENDPOINTS if e["expect_json"]]
    per_endpoint = 8.0 / max(len(json_endpoints), 1)

    for ep in json_endpoints:
        url = f"{api_url}{ep['path']}"
        try:
            if ep["method"] == "POST":
                resp = requests.post(
                    url,
                    json={"url": "https://example.com"},
                    timeout=timeout,
                )
            else:
                resp = requests.get(url, timeout=timeout)

            ct = resp.headers.get("content-type", "")
            is_json_ct = "application/json" in ct
            try:
                resp.json()
                is_valid_json = True
            except (json.JSONDecodeError, ValueError):
                is_valid_json = False

            ep_ok = is_json_ct and is_valid_json
            evidence["endpoints"][ep["path"]] = {
                "status": resp.status_code,
                "content_type": ct,
                "valid_json": is_valid_json,
                "pass": ep_ok,
            }

            if ep_ok:
                score += per_endpoint
            else:
                reason = []
                if not is_json_ct:
                    reason.append("wrong content-type")
                if not is_valid_json:
                    reason.append("invalid JSON body")
                findings.append(f"{ep['path']}: {', '.join(reason)}")

        except requests.RequestException as exc:
            findings.append(f"{ep['path']}: request failed ({exc})")
            evidence["endpoints"][ep["path"]] = {"error": str(exc)}

    # Bonus: check error envelope consistency
    error_responses = [
        v for v in evidence["endpoints"].values()
        if isinstance(v, dict) and v.get("status", 200) >= 400
    ]
    if not error_responses or all(v.get("valid_json") for v in error_responses):
        score += 2
        findings.append("Error responses use consistent JSON format")
    else:
        findings.append("Inconsistent error response format")

    if not findings:
        findings.append("All JSON endpoints return valid, consistent responses")

    return {
        "score": round(min(score, 10)),
        "max": 10,
        "findings": findings,
        "evidence": evidence,
    }


def assess_error_handling(api_url: str, timeout: float = 15) -> dict[str, Any]:
    """Send invalid requests and verify proper error responses.

    Scoring (0-10):
      - Each probe returning structured error JSON with status >= 400: +2.5 pts
    """
    score = 0.0
    findings: list[str] = []
    evidence: dict[str, Any] = {"probes": {}}
    per_probe = 10.0 / max(len(ERROR_PROBES), 1)

    for probe in ERROR_PROBES:
        url = f"{api_url}{probe['path']}"
        desc = probe["desc"]
        try:
            if probe["method"] == "POST":
                resp = requests.post(url, json=probe.get("body"), timeout=timeout)
            else:
                resp = requests.get(url, timeout=timeout)

            status = resp.status_code
            try:
                body = resp.json()
                has_error_field = "error" in body or "detail" in body
            except (json.JSONDecodeError, ValueError):
                body = None
                has_error_field = False

            probe_ok = status >= 400 and has_error_field
            evidence["probes"][desc] = {
                "status": status,
                "has_error_field": has_error_field,
                "pass": probe_ok,
            }

            if probe_ok:
                score += per_probe
                findings.append(f"{desc}: correct {status} with structured error")
            elif status >= 400:
                findings.append(f"{desc}: got {status} but missing structured error body")
            else:
                findings.append(f"{desc}: unexpected {status} (expected 4xx)")

        except requests.RequestException as exc:
            findings.append(f"{desc}: request failed ({exc})")
            evidence["probes"][desc] = {"error": str(exc)}

    return {
        "score": round(min(score, 10)),
        "max": 10,
        "findings": findings,
        "evidence": evidence,
    }


def assess_documentation(api_url: str, frontend_url: str, timeout: float = 15) -> dict[str, Any]:
    """Check documentation quality.

    Scoring (0-10):
      - /docs or /redoc reachable: 3 pts
      - Frontend has methodology page: 2 pts
      - API returns helpful error messages (not just status codes): 2 pts
      - OpenAPI has example values: 2 pts
      - README/changelog signal: 1 pt
    """
    score = 0
    findings: list[str] = []
    evidence: dict[str, Any] = {}

    # Check interactive docs
    for doc_path in ["/docs", "/redoc"]:
        try:
            resp = requests.get(f"{api_url}{doc_path}", timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                score += 3
                findings.append(f"Interactive docs available at {doc_path}")
                evidence["interactive_docs"] = doc_path
                break
        except requests.RequestException:
            pass
    else:
        findings.append("No interactive docs found (/docs or /redoc)")

    # Check methodology page on frontend
    try:
        resp = requests.get(
            f"{frontend_url}/methodology",
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            score += 2
            findings.append("Methodology page accessible")
        else:
            findings.append(f"Methodology page returned {resp.status_code}")
    except requests.RequestException as exc:
        findings.append(f"Could not reach methodology page: {exc}")

    # Check if error messages are helpful
    try:
        resp = requests.post(
            f"{api_url}/api/v1/scan",
            json={"url": ""},
            timeout=timeout,
        )
        body = resp.json() if resp.status_code >= 400 else {}
        error_msg = str(body.get("error", body.get("detail", "")))
        if len(error_msg) > 20:
            score += 2
            findings.append("Error messages are descriptive")
        else:
            findings.append("Error messages could be more descriptive")
    except (requests.RequestException, json.JSONDecodeError):
        findings.append("Could not evaluate error message quality")

    # Check OpenAPI examples
    try:
        resp = requests.get(f"{api_url}/openapi.json", timeout=timeout)
        if resp.status_code == 200:
            spec = resp.json()
            has_examples = False
            for path_data in spec.get("paths", {}).values():
                for method_data in path_data.values():
                    if isinstance(method_data, dict):
                        # Check for example in requestBody or responses
                        rb = method_data.get("requestBody", {})
                        if "example" in str(rb):
                            has_examples = True
                            break
                        for resp_data in method_data.get("responses", {}).values():
                            if "example" in str(resp_data):
                                has_examples = True
                                break
            if has_examples:
                score += 2
                findings.append("OpenAPI spec includes examples")
            else:
                findings.append("OpenAPI spec lacks request/response examples")
    except (requests.RequestException, json.JSONDecodeError):
        findings.append("Could not evaluate OpenAPI examples")

    # GitHub/changelog signal
    try:
        resp = requests.get(f"{api_url}/health", timeout=timeout)
        body = resp.json() if resp.status_code == 200 else {}
        if body.get("version") or body.get("build"):
            score += 1
            findings.append("Version info exposed in health endpoint")
        else:
            findings.append("No version info in health endpoint")
    except (requests.RequestException, json.JSONDecodeError):
        pass

    return {
        "score": min(score, 10),
        "max": 10,
        "findings": findings,
        "evidence": evidence,
    }


def assess_performance(api_url: str, timeout: float = 15, samples: int = 3) -> dict[str, Any]:
    """Measure average response time across key endpoints.

    Scoring (0-10):
      - Average < 200ms: 10 pts
      - Average < 500ms: 8 pts
      - Average < 1000ms: 6 pts
      - Average < 2000ms: 4 pts
      - Average < 5000ms: 2 pts
      - Otherwise: 0 pts
    """
    latencies: list[float] = []
    findings: list[str] = []
    evidence: dict[str, Any] = {"endpoints": {}}

    perf_endpoints = [
        {"path": "/health", "method": "GET"},
        {"path": "/api/v1/index", "method": "GET"},
        {"path": "/api/v1/trending", "method": "GET"},
    ]

    for ep in perf_endpoints:
        url = f"{api_url}{ep['path']}"
        ep_latencies = []
        for _ in range(samples):
            try:
                start = time.monotonic()
                requests.get(url, timeout=timeout)
                elapsed = (time.monotonic() - start) * 1000  # ms
                ep_latencies.append(elapsed)
            except requests.RequestException:
                pass
            time.sleep(0.1)  # small delay between samples

        if ep_latencies:
            avg = sum(ep_latencies) / len(ep_latencies)
            latencies.extend(ep_latencies)
            evidence["endpoints"][ep["path"]] = {
                "avg_ms": round(avg, 1),
                "samples": len(ep_latencies),
            }
            findings.append(f"{ep['path']}: avg {avg:.0f}ms ({len(ep_latencies)} samples)")

    if not latencies:
        return {
            "score": 0,
            "max": 10,
            "findings": ["Could not measure performance — all requests failed"],
            "evidence": evidence,
        }

    avg_latency = sum(latencies) / len(latencies)
    evidence["overall_avg_ms"] = round(avg_latency, 1)

    if avg_latency < 200:
        score = 10
    elif avg_latency < 500:
        score = 8
    elif avg_latency < 1000:
        score = 6
    elif avg_latency < 2000:
        score = 4
    elif avg_latency < 5000:
        score = 2
    else:
        score = 0

    findings.append(f"Overall average: {avg_latency:.0f}ms -> {score}/10")

    return {
        "score": score,
        "max": 10,
        "findings": findings,
        "evidence": evidence,
    }


def assess_availability(api_url: str, timeout: float = 15) -> dict[str, Any]:
    """Check current availability and parse recent healthcheck logs.

    Scoring (0-10):
      - API responds right now: 5 pts
      - Frontend responds right now: 3 pts
      - Healthcheck log shows >= 99% uptime: 2 pts (or 1 pt for >= 95%)
    """
    score = 0
    findings: list[str] = []
    evidence: dict[str, Any] = {}

    # Live API check
    try:
        resp = requests.get(f"{api_url}/health", timeout=timeout)
        if resp.status_code == 200:
            score += 5
            findings.append("API is currently healthy")
            evidence["api_status"] = "healthy"
        else:
            findings.append(f"API health returned {resp.status_code}")
            evidence["api_status"] = f"unhealthy ({resp.status_code})"
    except requests.RequestException as exc:
        findings.append(f"API unreachable: {exc}")
        evidence["api_status"] = "unreachable"

    # Live frontend check
    frontend_url = DEFAULT_FRONTEND_URL
    try:
        resp = requests.get(frontend_url, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            score += 3
            findings.append("Frontend is currently accessible")
            evidence["frontend_status"] = "healthy"
        else:
            findings.append(f"Frontend returned {resp.status_code}")
            evidence["frontend_status"] = f"unhealthy ({resp.status_code})"
    except requests.RequestException as exc:
        findings.append(f"Frontend unreachable: {exc}")
        evidence["frontend_status"] = "unreachable"

    # Parse healthcheck log for uptime
    log_path = DATA_DIR / "healthcheck.log"
    if log_path.exists():
        try:
            lines = log_path.read_text().strip().split("\n")[-200:]  # last 200 entries
            total = len(lines)
            successes = sum(1 for l in lines if '"healthy"' in l or "OK" in l)
            if total > 0:
                uptime_pct = (successes / total) * 100
                evidence["log_uptime_pct"] = round(uptime_pct, 2)
                evidence["log_entries_analyzed"] = total
                if uptime_pct >= 99:
                    score += 2
                    findings.append(f"Historical uptime: {uptime_pct:.1f}%")
                elif uptime_pct >= 95:
                    score += 1
                    findings.append(f"Historical uptime: {uptime_pct:.1f}% (below 99%)")
                else:
                    findings.append(f"Historical uptime: {uptime_pct:.1f}% (needs improvement)")
        except Exception as exc:
            findings.append(f"Could not parse healthcheck log: {exc}")
    else:
        findings.append("No healthcheck log found — consider enabling healthcheck automation")

    return {
        "score": min(score, 10),
        "max": 10,
        "findings": findings,
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# Improvement suggestion generator
# ---------------------------------------------------------------------------

IMPROVEMENT_TEMPLATES = {
    "api_discoverability": [
        {
            "condition": lambda s: s < 4,
            "action": "Add /openapi.json endpoint — FastAPI generates this automatically when docs are enabled",
            "estimated_impact": "high",
        },
        {
            "condition": lambda s: 4 <= s < 8,
            "action": "Add server URLs and description to OpenAPI spec info section",
            "estimated_impact": "medium",
        },
        {
            "condition": lambda s: s < 10,
            "action": "Ensure all routes are documented with request/response schemas in OpenAPI",
            "estimated_impact": "low",
        },
    ],
    "response_format": [
        {
            "condition": lambda s: s < 8,
            "action": "Standardize all error responses to use {error: {type, message}} envelope",
            "estimated_impact": "high",
        },
        {
            "condition": lambda s: s < 10,
            "action": "Add Content-Type: application/json header to all API responses",
            "estimated_impact": "medium",
        },
    ],
    "error_handling": [
        {
            "condition": lambda s: s < 5,
            "action": "Add global exception handler returning structured JSON for all 4xx/5xx",
            "estimated_impact": "high",
        },
        {
            "condition": lambda s: s < 8,
            "action": "Return descriptive error messages with suggested fixes in error responses",
            "estimated_impact": "medium",
        },
    ],
    "documentation": [
        {
            "condition": lambda s: s < 5,
            "action": "Enable FastAPI /docs and /redoc interactive documentation endpoints",
            "estimated_impact": "high",
        },
        {
            "condition": lambda s: s < 8,
            "action": "Add request/response examples to all OpenAPI operation definitions",
            "estimated_impact": "medium",
        },
        {
            "condition": lambda s: s < 10,
            "action": "Expose version and build info in /health endpoint response",
            "estimated_impact": "low",
        },
    ],
    "performance": [
        {
            "condition": lambda s: s < 6,
            "action": "Investigate slow endpoints — add caching, optimize DB queries, or reduce payload size",
            "estimated_impact": "high",
        },
        {
            "condition": lambda s: s < 8,
            "action": "Add response compression (gzip) and consider CDN for static data",
            "estimated_impact": "medium",
        },
    ],
    "availability": [
        {
            "condition": lambda s: s < 5,
            "action": "Configure auto-recovery: Render auto-deploy on failure or add keep-alive pings",
            "estimated_impact": "high",
        },
        {
            "condition": lambda s: s < 8,
            "action": "Set up redundant healthcheck from multiple regions",
            "estimated_impact": "medium",
        },
    ],
}


def generate_suggestions(breakdown: dict[str, dict]) -> list[dict[str, str]]:
    """Generate top improvement suggestions based on assessment gaps."""
    suggestions: list[dict[str, str]] = []

    for area, result in breakdown.items():
        templates = IMPROVEMENT_TEMPLATES.get(area, [])
        score = result["score"]
        for tmpl in templates:
            if tmpl["condition"](score):
                suggestions.append({
                    "area": area,
                    "action": tmpl["action"],
                    "estimated_impact": tmpl["estimated_impact"],
                    "current_score": f"{score}/{result['max']}",
                })

    # Sort by impact: high > medium > low
    impact_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: impact_order.get(s["estimated_impact"], 3))

    return suggestions[:5]  # top 5 suggestions


# ---------------------------------------------------------------------------
# Previous assessment loader
# ---------------------------------------------------------------------------

def load_previous_assessment() -> Optional[dict]:
    """Load the most recent previous self-assessment."""
    if not SELF_IMPROVEMENT_DIR.exists():
        return None

    files = sorted(SELF_IMPROVEMENT_DIR.glob("assessment-*.json"), reverse=True)
    # Skip today's file if it exists
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for f in files:
        if today_str not in f.name:
            try:
                return json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
    return None


def compute_improvements_since(current: dict, previous: Optional[dict]) -> list[str]:
    """List areas that improved since the last assessment."""
    if not previous:
        return ["First assessment — no previous data to compare"]

    improvements = []
    prev_breakdown = previous.get("breakdown", {})

    for area, result in current.items():
        prev = prev_breakdown.get(area, {})
        prev_score = prev.get("score", 0)
        curr_score = result["score"]
        if curr_score > prev_score:
            improvements.append(
                f"{area}: {prev_score}/{result['max']} -> {curr_score}/{result['max']}"
            )

    return improvements if improvements else ["No score improvements since last assessment"]


# ---------------------------------------------------------------------------
# Main assessment runner
# ---------------------------------------------------------------------------

def run_self_assessment(
    api_url: str = DEFAULT_API_URL,
    frontend_url: str = DEFAULT_FRONTEND_URL,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run full self-assessment and save results."""
    logger.info("Starting Clarvia self-assessment against %s", api_url)

    breakdown = {
        "api_discoverability": assess_api_discoverability(api_url),
        "response_format": assess_response_format(api_url),
        "error_handling": assess_error_handling(api_url),
        "documentation": assess_documentation(api_url, frontend_url),
        "performance": assess_performance(api_url),
        "availability": assess_availability(api_url),
    }

    # Calculate overall score (weighted average, normalized to 10)
    total_score = sum(d["score"] for d in breakdown.values())
    total_max = sum(d["max"] for d in breakdown.values())
    overall = round((total_score / total_max) * 10, 1) if total_max > 0 else 0

    # Load previous and compute delta
    previous = load_previous_assessment()
    previous_score = previous.get("overall_score") if previous else None
    improvements_since = compute_improvements_since(breakdown, previous)

    # Generate suggestions
    suggestions = generate_suggestions(breakdown)

    # Build assessment document
    now = datetime.now(timezone.utc)
    assessment = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "overall_score": overall,
        "breakdown": {
            area: {
                "score": result["score"],
                "max": result["max"],
                "findings": result["findings"],
            }
            for area, result in breakdown.items()
        },
        "previous_score": previous_score,
        "improvements_since_last": improvements_since,
        "suggested_next": suggestions,
    }

    # Save
    filename = f"assessment-{now.strftime('%Y-%m-%d')}.json"
    output_path = SELF_IMPROVEMENT_DIR / filename

    if dry_run:
        logger.info("[DRY RUN] Would save to %s", output_path)
        logger.info(json.dumps(assessment, indent=2))
    else:
        output_path.write_text(json.dumps(assessment, indent=2))
        logger.info("Assessment saved to %s", output_path)

    # Log summary
    logger.info(
        "Self-assessment complete: %.1f/10 (previous: %s)",
        overall,
        f"{previous_score}/10" if previous_score is not None else "N/A",
    )
    for s in suggestions[:3]:
        logger.info("  Suggestion [%s]: %s", s["estimated_impact"], s["action"])

    # Send Telegram notification on significant change
    if previous_score is not None and not dry_run:
        delta = overall - previous_score
        if abs(delta) >= 0.5:
            direction = "improved" if delta > 0 else "declined"
            send_alert(
                f"Clarvia Self-Assessment: {direction}",
                (
                    f"Score: {previous_score} -> {overall}/10 ({'+' if delta > 0 else ''}{delta:.1f})\n\n"
                    f"Top suggestion: {suggestions[0]['action'] if suggestions else 'None'}"
                ),
                level="SUCCESS" if delta > 0 else "WARNING",
            )

    return assessment


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Clarvia Self-Improvement Engine — assess and improve your own AEO score"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Clarvia API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--frontend-url",
        default=DEFAULT_FRONTEND_URL,
        help=f"Clarvia frontend URL (default: {DEFAULT_FRONTEND_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without saving or alerting",
    )
    args = parser.parse_args()

    result = run_self_assessment(
        api_url=args.api_url,
        frontend_url=args.frontend_url,
        dry_run=args.dry_run,
    )

    # Print summary to stdout
    print(f"\nClarvia Self-Assessment: {result['overall_score']}/10")
    print("-" * 40)
    for area, data in result["breakdown"].items():
        print(f"  {area}: {data['score']}/{data['max']}")
    print()
    if result["suggested_next"]:
        print("Top suggestions:")
        for i, s in enumerate(result["suggested_next"][:3], 1):
            print(f"  {i}. [{s['estimated_impact']}] {s['action']}")
    print()


if __name__ == "__main__":
    main()
