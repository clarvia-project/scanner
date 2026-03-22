"""Trust Signals checks (25 points).

Sub-factors:
- Success Rate & Uptime (10 pts)
- Documentation Quality (8 pts)
- Update Frequency (7 pts)
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import aiohttp

from ..config import settings


async def check_uptime(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Look for status page / uptime monitoring (10 pts max).

    Since we can't measure 30-day uptime in a single scan, we look for
    public status page presence as a proxy for reliability practices.
    """
    domain = urlparse(base_url).hostname or ""
    bare_domain = domain.replace("www.", "")
    company = bare_domain.split(".")[0]

    status_urls = [
        f"https://status.{bare_domain}",
        f"https://{company}.statuspage.io",
        f"https://{bare_domain}/status",
        f"{base_url}/status",
        f"https://status.{company}.com",
        f"https://{company}.upptime.js.org",
    ]

    for url in status_urls:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = await resp.text()
                    text_lower = text.lower()

                    # Look for uptime indicators
                    if any(kw in text_lower for kw in [
                        "operational", "uptime", "all systems",
                        "no incidents", "status page",
                    ]):
                        return (7, {
                            "reason": "Public status page found with operational indicators",
                            "url": url,
                        })
                    else:
                        return (4, {
                            "reason": "Status page found",
                            "url": url,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # No status page found — give 1 point if the main site responds reliably
    try:
        async with session.get(
            base_url, timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True, ssl=False,
        ) as resp:
            if resp.status < 300:
                return (1, {
                    "reason": "No status page but site is currently responsive",
                })
    except Exception:
        pass

    return (0, {"reason": "No uptime data available"})


async def check_documentation_quality(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Evaluate documentation depth (8 pts max).

    8 pts = Comprehensive docs (guides, tutorials, API ref, changelogs, 3+ lang examples)
    5 pts = Good API reference with some guides
    3 pts = Basic API reference only
    1 pt  = Minimal or outdated docs
    0 pts = No documentation
    """
    domain = urlparse(base_url).hostname or ""
    bare_domain = domain.replace("www.", "")
    company = bare_domain.split(".")[0]

    docs_urls = [
        f"{base_url}/docs",
        f"{base_url}/documentation",
        f"https://docs.{bare_domain}",
        f"{base_url}/api",
        f"{base_url}/reference",
        f"{base_url}/developers",
    ]

    best_score = 0
    best_evidence: dict[str, Any] = {"reason": "No documentation found"}

    for url in docs_urls:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status >= 300:
                    continue

                text = await resp.text()
                text_lower = text.lower()

                # Count documentation quality signals
                signals = {
                    "api_reference": any(kw in text_lower for kw in ["api reference", "endpoints", "api documentation"]),
                    "guides": any(kw in text_lower for kw in ["guide", "tutorial", "getting started", "quickstart"]),
                    "changelog": any(kw in text_lower for kw in ["changelog", "release notes", "what's new"]),
                    "code_examples": any(kw in text_lower for kw in ["```", "code example", "sample code", "sdk"]),
                    "multi_language": sum(1 for lang in ["python", "javascript", "ruby", "go", "java", "curl", "php", "c#", "rust"]
                                         if lang in text_lower) >= 3,
                }

                signal_count = sum(signals.values())

                if signal_count >= 4:
                    score = 8
                    reason = "Comprehensive documentation"
                elif signal_count >= 3:
                    score = 5
                    reason = "Good API reference with some guides"
                elif signal_count >= 1:
                    score = 3
                    reason = "Basic API reference"
                else:
                    score = 1
                    reason = "Minimal documentation page"

                if score > best_score:
                    best_score = score
                    best_evidence = {
                        "reason": reason,
                        "url": url,
                        "signals": {k: v for k, v in signals.items() if v},
                    }

        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (best_score, best_evidence)


async def check_update_frequency(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for recent updates via changelog, last-modified headers (7 pts max).

    7 pts = Updated within 30 days with changelog
    5 pts = Updated within 90 days
    3 pts = Updated within 180 days
    1 pt  = Updated within 1 year
    0 pts = No updates in 1+ year
    """
    domain = urlparse(base_url).hostname or ""
    bare_domain = domain.replace("www.", "")

    changelog_urls = [
        f"{base_url}/changelog",
        f"{base_url}/docs/changelog",
        f"https://docs.{bare_domain}/changelog",
        f"{base_url}/blog",
        f"{base_url}/updates",
        f"{base_url}/releases",
    ]

    now = datetime.now(timezone.utc)

    for url in changelog_urls:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status >= 300:
                    continue

                # Check last-modified header
                last_modified = resp.headers.get("last-modified")
                if last_modified:
                    try:
                        from email.utils import parsedate_to_datetime
                        lm_dt = parsedate_to_datetime(last_modified)
                        days_old = (now - lm_dt).days
                        if days_old <= 30:
                            return (7, {
                                "reason": "Updated within 30 days",
                                "url": url,
                                "last_modified": last_modified,
                                "days_ago": days_old,
                            })
                        elif days_old <= 90:
                            return (5, {"reason": "Updated within 90 days", "url": url, "days_ago": days_old})
                        elif days_old <= 180:
                            return (3, {"reason": "Updated within 180 days", "url": url, "days_ago": days_old})
                        elif days_old <= 365:
                            return (1, {"reason": "Updated within 1 year", "url": url, "days_ago": days_old})
                    except Exception:
                        pass

                # Check page content for recent dates (YYYY-MM-DD or Month DD, YYYY)
                text = await resp.text()
                text_lower = text.lower()

                if any(kw in text_lower for kw in ["changelog", "release", "update", "version"]):
                    # Assume recent if changelog page exists and is accessible
                    return (5, {
                        "reason": "Changelog/updates page found",
                        "url": url,
                    })

        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Fallback: check last-modified on main URL
    try:
        async with session.head(
            base_url, timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True, ssl=False,
        ) as resp:
            last_modified = resp.headers.get("last-modified")
            if last_modified:
                try:
                    from email.utils import parsedate_to_datetime
                    lm_dt = parsedate_to_datetime(last_modified)
                    days_old = (now - lm_dt).days
                    if days_old <= 30:
                        return (5, {"reason": "Main page updated recently", "days_ago": days_old})
                    elif days_old <= 90:
                        return (3, {"reason": "Main page updated within 90 days", "days_ago": days_old})
                except Exception:
                    pass
    except Exception:
        pass

    return (0, {"reason": "No update frequency data available"})


async def run_trust_signals(
    session: aiohttp.ClientSession, base_url: str
) -> dict:
    """Run all Trust Signal checks concurrently."""
    uptime_task = check_uptime(session, base_url)
    docs_task = check_documentation_quality(session, base_url)
    update_task = check_update_frequency(session, base_url)

    (uptime_score, uptime_ev), (docs_score, docs_ev), (update_score, update_ev) = (
        await asyncio.gather(uptime_task, docs_task, update_task)
    )

    total = uptime_score + docs_score + update_score

    return {
        "score": total,
        "max": 25,
        "sub_factors": {
            "success_rate_uptime": {
                "score": uptime_score,
                "max": 10,
                "label": "Success Rate & Uptime",
                "evidence": uptime_ev,
            },
            "documentation_quality": {
                "score": docs_score,
                "max": 8,
                "label": "Documentation Quality",
                "evidence": docs_ev,
            },
            "update_frequency": {
                "score": update_score,
                "max": 7,
                "label": "Update Frequency",
                "evidence": update_ev,
            },
        },
    }
