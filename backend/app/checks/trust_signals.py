"""Trust Signals checks (25 points).

Sub-factors:
- Success Rate & Uptime (6 pts)
- Documentation Quality (5 pts)
- Update Frequency (4 pts)
- Response Consistency (4 pts)
- Error Response Quality (3 pts)
- Deprecation Policy (2 pts)
- SLA / Uptime Guarantee (1 pt)
"""

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import aiohttp

from ..config import settings


async def check_uptime(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Look for status page / uptime monitoring (6 pts max)."""
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

    async def _check_status_url(url: str) -> tuple[int, dict] | None:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = await resp.text()
                    text_lower = text.lower()
                    if any(kw in text_lower for kw in [
                        "operational", "uptime", "all systems",
                        "no incidents", "status page",
                    ]):
                        return (6, {"reason": "Public status page found with operational indicators", "url": url})
                    return (3, {"reason": "Status page found", "url": url})
        except Exception:
            pass
        return None

    results = await asyncio.gather(*[_check_status_url(u) for u in status_urls])
    for r in results:
        if r is not None:
            return r

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
    """Evaluate documentation depth (5 pts max).

    5 pts = Comprehensive docs (guides, tutorials, API ref, changelogs, 3+ lang examples)
    4 pts = Good API reference with some guides
    2 pts = Basic API reference only
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
        f"https://developer.{bare_domain}",
        f"https://developers.{bare_domain}",
        f"{base_url}/api",
        f"{base_url}/reference",
        f"{base_url}/developers",
        f"https://docs.{bare_domain}/api",
        f"https://docs.{bare_domain}/reference",
    ]

    async def _check_docs_url(url: str) -> tuple[int, dict]:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status >= 300:
                    return (0, {})

                text = await resp.text()
                text_lower = text.lower()

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
                    score, reason = 5, "Comprehensive documentation"
                elif signal_count >= 3:
                    score, reason = 4, "Good API reference with some guides"
                elif signal_count >= 1:
                    score, reason = 2, "Basic API reference"
                else:
                    score, reason = 1, "Minimal documentation page"

                return (score, {"reason": reason, "url": url, "signals": {k: v for k, v in signals.items() if v}})
        except Exception:
            return (0, {})

    results = await asyncio.gather(*[_check_docs_url(u) for u in docs_urls])
    best_score = 0
    best_evidence: dict[str, Any] = {"reason": "No documentation found"}
    for score, ev in results:
        if score > best_score:
            best_score = score
            best_evidence = ev

    return (best_score, best_evidence)


async def check_update_frequency(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for recent updates via changelog, last-modified headers (4 pts max).

    4 pts = Updated within 30 days with changelog
    3 pts = Updated within 90 days
    2 pts = Updated within 180 days
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

                last_modified = resp.headers.get("last-modified")
                if last_modified:
                    try:
                        from email.utils import parsedate_to_datetime
                        lm_dt = parsedate_to_datetime(last_modified)
                        days_old = (now - lm_dt).days
                        if days_old <= 30:
                            return (4, {
                                "reason": "Updated within 30 days",
                                "url": url,
                                "last_modified": last_modified,
                                "days_ago": days_old,
                            })
                        elif days_old <= 90:
                            return (3, {"reason": "Updated within 90 days", "url": url, "days_ago": days_old})
                        elif days_old <= 180:
                            return (2, {"reason": "Updated within 180 days", "url": url, "days_ago": days_old})
                        elif days_old <= 365:
                            return (1, {"reason": "Updated within 1 year", "url": url, "days_ago": days_old})
                    except Exception:
                        pass

                text = await resp.text()
                text_lower = text.lower()

                if any(kw in text_lower for kw in ["changelog", "release", "update", "version"]):
                    return (3, {
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
                        return (3, {"reason": "Main page updated recently", "days_ago": days_old})
                    elif days_old <= 90:
                        return (2, {"reason": "Main page updated within 90 days", "days_ago": days_old})
                except Exception:
                    pass
    except Exception:
        pass

    return (0, {"reason": "No update frequency data available"})


async def check_response_consistency(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check response consistency by making the same request 3 times (4 pts max).

    4 pts = All 3 responses identical (status + key headers + body hash)
    2 pts = Status codes match but content varies slightly
    0 pts = Inconsistent responses
    """
    probe_urls = [
        f"{base_url}/api",
        f"{base_url}/api/v1",
        base_url,
    ]

    for probe_url in probe_urls:
        statuses: list[int] = []
        content_hashes: list[str] = []
        content_types: list[str] = []

        for _ in range(3):
            try:
                async with session.get(
                    probe_url, timeout=aiohttp.ClientTimeout(total=5),
                    allow_redirects=True, ssl=False,
                ) as resp:
                    statuses.append(resp.status)
                    content_types.append(resp.headers.get("content-type", ""))
                    body = await resp.read()
                    content_hashes.append(hashlib.md5(body).hexdigest())
            except (aiohttp.ClientError, asyncio.TimeoutError):
                statuses.append(-1)
                content_hashes.append("")
                content_types.append("")
            await asyncio.sleep(0.3)

        # Need at least 3 successful responses
        if all(s > 0 for s in statuses):
            all_same_status = len(set(statuses)) == 1
            all_same_hash = len(set(content_hashes)) == 1
            all_same_ct = len(set(content_types)) == 1

            if all_same_status and all_same_hash:
                return (4, {
                    "reason": "All 3 responses identical (status, headers, body)",
                    "url": probe_url,
                    "status": statuses[0],
                })
            elif all_same_status:
                return (2, {
                    "reason": "Status codes consistent but content varies (dynamic content)",
                    "url": probe_url,
                    "status": statuses[0],
                    "unique_hashes": len(set(content_hashes)),
                })
            else:
                return (0, {
                    "reason": "Inconsistent responses across requests",
                    "url": probe_url,
                    "statuses": statuses,
                })

    return (0, {"reason": "Could not test response consistency"})


async def check_error_response_quality(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check error response quality beyond structure (3 pts max).

    3 pts = Error includes code, message, AND documentation link
    2 pts = Error includes code and descriptive message
    1 pt  = Basic error message
    0 pts = No structured errors or HTML errors
    """
    probe_urls = [
        f"{base_url}/api/nonexistent-test-12345",
        f"{base_url}/v1/nonexistent-test-12345",
        f"{base_url}/nonexistent-test-12345",
    ]

    for probe_url in probe_urls:
        try:
            async with session.get(
                probe_url, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                ct = resp.headers.get("content-type", "")
                if resp.status >= 400 and "json" in ct:
                    try:
                        data = await resp.json()
                        if isinstance(data, dict):
                            has_code = "code" in data or "error_code" in data or "status" in data
                            has_message = "message" in data or "detail" in data or "error" in data
                            # Check for documentation link in error
                            data_str = str(data).lower()
                            has_doc_link = any(kw in data_str for kw in [
                                "docs", "documentation", "doc_url", "more_info",
                                "help_url", "reference", "https://",
                            ])

                            if has_code and has_message and has_doc_link:
                                return (3, {
                                    "reason": "Error includes code, message, and documentation link",
                                    "url": probe_url,
                                    "status": resp.status,
                                    "error_keys": list(data.keys())[:8],
                                })
                            elif has_code and has_message:
                                return (2, {
                                    "reason": "Error includes code and descriptive message",
                                    "url": probe_url,
                                    "status": resp.status,
                                    "error_keys": list(data.keys())[:8],
                                })
                            elif has_message:
                                return (1, {
                                    "reason": "Basic error message in response",
                                    "url": probe_url,
                                    "status": resp.status,
                                })
                    except Exception:
                        pass
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No structured error responses found"})


async def check_deprecation_policy(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for deprecation policy documentation (2 pts max).

    2 pts = Explicit deprecation/versioning policy documented
    1 pt  = Deprecation or sunset mentioned
    0 pts = No deprecation policy found
    """
    policy_paths = [
        f"{base_url}/docs/deprecation",
        f"{base_url}/docs/versioning",
        f"{base_url}/docs/api-versioning",
        f"{base_url}/docs/migration",
        f"{base_url}/docs",
        f"{base_url}/docs/api",
    ]

    for path in policy_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = (await resp.text()).lower()
                    deprecation_keywords = [
                        "deprecation policy", "sunset policy", "api lifecycle",
                        "versioning policy", "migration guide", "breaking change",
                        "end of life", "deprecated",
                    ]
                    strong_matches = [kw for kw in deprecation_keywords[:4] if kw in text]
                    weak_matches = [kw for kw in deprecation_keywords[4:] if kw in text]

                    if strong_matches:
                        return (2, {
                            "reason": "Explicit deprecation/versioning policy documented",
                            "url": path,
                            "keywords": strong_matches,
                        })
                    elif weak_matches:
                        return (1, {
                            "reason": "Deprecation or migration mentioned",
                            "url": path,
                            "keywords": weak_matches,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Check for Sunset or Deprecation headers in API responses
    api_paths = [base_url, f"{base_url}/api", f"{base_url}/v1"]
    for path in api_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                sunset = resp.headers.get("sunset")
                deprecation = resp.headers.get("deprecation")
                if sunset or deprecation:
                    return (2, {
                        "reason": "Sunset/Deprecation headers in API response",
                        "url": path,
                        "sunset": sunset,
                        "deprecation": deprecation,
                    })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No deprecation policy found"})


async def check_sla_guarantee(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for published SLA or uptime guarantee (1 pt max).

    1 pt  = SLA/uptime guarantee published
    0 pts = No SLA found
    """
    sla_paths = [
        f"{base_url}/sla",
        f"{base_url}/docs/sla",
        f"{base_url}/terms",
        f"{base_url}/legal/sla",
        f"{base_url}/pricing",
    ]

    for path in sla_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = (await resp.text()).lower()
                    sla_keywords = [
                        "service level agreement", "sla", "uptime guarantee",
                        "99.9%", "99.99%", "99.95%", "guaranteed uptime",
                        "availability commitment",
                    ]
                    if any(kw in text for kw in sla_keywords):
                        return (1, {
                            "reason": "SLA or uptime guarantee published",
                            "url": path,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No SLA/uptime guarantee found"})


async def check_github_activity(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check GitHub org/repo for stars and recent activity as a trust signal.

    Returns a bonus score (0-2) that can boost uptime scores.
    """
    domain = urlparse(base_url).hostname or ""
    company = domain.replace("www.", "").split(".")[0]

    github_api = f"https://api.github.com/search/repositories?q=org:{company}&sort=stars&per_page=5"

    try:
        async with session.get(
            github_api,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True, ssl=False,
            headers={"Accept": "application/vnd.github.v3+json"},
        ) as resp:
            if resp.status < 300:
                data = await resp.json()
                items = data.get("items", [])
                if items:
                    total_stars = sum(r.get("stargazers_count", 0) for r in items)
                    top_repo = items[0]
                    pushed_at = top_repo.get("pushed_at", "")

                    activity_score = 0
                    evidence: dict[str, Any] = {
                        "github_org": company,
                        "total_stars": total_stars,
                        "top_repo": top_repo.get("full_name"),
                        "last_push": pushed_at,
                    }

                    if total_stars >= 1000:
                        activity_score = 2
                        evidence["reason"] = "Active GitHub presence with 1000+ stars"
                    elif total_stars >= 100:
                        activity_score = 1
                        evidence["reason"] = "GitHub presence with 100+ stars"

                    return (activity_score, evidence)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    return (0, {"reason": "No GitHub activity data found"})


async def run_trust_signals(
    session: aiohttp.ClientSession, base_url: str
) -> dict:
    """Run all Trust Signal checks concurrently."""
    (uptime_score, uptime_ev), (docs_score, docs_ev), (update_score, update_ev), \
        (consistency_score, consistency_ev), (error_quality_score, error_quality_ev), \
        (deprecation_score, deprecation_ev), (sla_score, sla_ev), \
        (gh_score, gh_ev) = await asyncio.gather(
        check_uptime(session, base_url),
        check_documentation_quality(session, base_url),
        check_update_frequency(session, base_url),
        check_response_consistency(session, base_url),
        check_error_response_quality(session, base_url),
        check_deprecation_policy(session, base_url),
        check_sla_guarantee(session, base_url),
        check_github_activity(session, base_url),
    )

    # GitHub activity boosts uptime score (capped at 6)
    if gh_score > 0 and uptime_score < 6:
        bonus = min(gh_score, 6 - uptime_score)
        uptime_score += bonus
        uptime_ev["github_bonus"] = bonus
        uptime_ev["github_evidence"] = gh_ev

    total = uptime_score + docs_score + update_score + consistency_score + error_quality_score + deprecation_score + sla_score

    return {
        "score": total,
        "max": 25,
        "sub_factors": {
            "success_rate_uptime": {
                "score": uptime_score,
                "max": 6,
                "label": "Success Rate & Uptime",
                "evidence": uptime_ev,
            },
            "documentation_quality": {
                "score": docs_score,
                "max": 5,
                "label": "Documentation Quality",
                "evidence": docs_ev,
            },
            "update_frequency": {
                "score": update_score,
                "max": 4,
                "label": "Update Frequency",
                "evidence": update_ev,
            },
            "response_consistency": {
                "score": consistency_score,
                "max": 4,
                "label": "Response Consistency",
                "evidence": consistency_ev,
            },
            "error_response_quality": {
                "score": error_quality_score,
                "max": 3,
                "label": "Error Response Quality",
                "evidence": error_quality_ev,
            },
            "deprecation_policy": {
                "score": deprecation_score,
                "max": 2,
                "label": "Deprecation Policy",
                "evidence": deprecation_ev,
            },
            "sla_guarantee": {
                "score": sla_score,
                "max": 1,
                "label": "SLA / Uptime Guarantee",
                "evidence": sla_ev,
            },
        },
    }
