"""External data enrichment service — fetches real signals from free APIs.

Free APIs used:
- npm registry (https://registry.npmjs.org) — downloads, license, dependencies
- PyPI (https://pypi.org/pypi/{pkg}/json) — package metadata
- OSV.dev (https://api.osv.dev/v1/query) — CVE/vulnerability data (Google)
- GitHub API (https://api.github.com) — stars, forks, last commit (60 req/hr unauthed)
"""

import asyncio
import logging
import re
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid hitting rate limits
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 3600  # 1 hour


def _get_cached(key: str) -> Any | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: Any) -> None:
    _cache[key] = (time.time(), data)
    # Evict old entries if cache gets too large
    if len(_cache) > 1000:
        cutoff = time.time() - _CACHE_TTL
        stale = [k for k, (ts, _) in _cache.items() if ts < cutoff]
        for k in stale:
            del _cache[k]


async def _fetch_json(url: str, timeout: int = 10) -> dict | None:
    """Fetch JSON from URL with timeout and error handling."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.debug("HTTP %d from %s", resp.status, url)
                return None
    except Exception as e:
        logger.debug("Fetch failed for %s: %s", url, e)
        return None


async def _post_json(url: str, body: dict, timeout: int = 10) -> dict | None:
    """POST JSON and return response."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=body,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    except Exception as e:
        logger.debug("POST failed for %s: %s", url, e)
        return None


# --- npm Registry ------------------------------------------------------------

async def enrich_npm(package_name: str) -> dict[str, Any]:
    """Fetch real npm package data: downloads, license, dependencies, version."""
    cache_key = f"npm:{package_name}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: dict[str, Any] = {"source": "npm", "package": package_name}

    # Package metadata
    meta = await _fetch_json(f"https://registry.npmjs.org/{package_name}")
    if meta:
        latest_ver = meta.get("dist-tags", {}).get("latest", "")
        latest_data = meta.get("versions", {}).get(latest_ver, {})

        result["version"] = latest_ver
        result["license"] = meta.get("license") or latest_data.get("license", "")
        result["description"] = meta.get("description", "")
        result["homepage"] = meta.get("homepage", "")
        result["repository"] = ""
        repo = meta.get("repository")
        if isinstance(repo, dict):
            result["repository"] = repo.get("url", "")
        elif isinstance(repo, str):
            result["repository"] = repo
        result["dependencies_count"] = len(latest_data.get("dependencies", {}))
        result["dev_dependencies_count"] = len(latest_data.get("devDependencies", {}))
        result["keywords"] = meta.get("keywords", [])[:10]

        # Maintainers
        maintainers = meta.get("maintainers", [])
        result["maintainers_count"] = len(maintainers)

        # Created/modified dates
        time_data = meta.get("time", {})
        result["created"] = time_data.get("created", "")
        result["last_published"] = time_data.get(latest_ver, "")

    # Weekly downloads (separate API)
    dl = await _fetch_json(f"https://api.npmjs.org/downloads/point/last-week/{package_name}")
    if dl:
        result["weekly_downloads"] = dl.get("downloads", 0)
    else:
        result["weekly_downloads"] = 0

    # Monthly downloads
    dl_month = await _fetch_json(f"https://api.npmjs.org/downloads/point/last-month/{package_name}")
    if dl_month:
        result["monthly_downloads"] = dl_month.get("downloads", 0)
    else:
        result["monthly_downloads"] = 0

    _set_cache(cache_key, result)
    return result


# --- PyPI ---------------------------------------------------------------------

async def enrich_pypi(package_name: str) -> dict[str, Any]:
    """Fetch PyPI package metadata."""
    cache_key = f"pypi:{package_name}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: dict[str, Any] = {"source": "pypi", "package": package_name}

    data = await _fetch_json(f"https://pypi.org/pypi/{package_name}/json")
    if data:
        info = data.get("info", {})
        result["version"] = info.get("version", "")
        result["license"] = info.get("license", "")
        result["description"] = info.get("summary", "")
        result["homepage"] = info.get("home_page") or info.get("project_url", "")
        result["author"] = info.get("author", "")
        result["requires_python"] = info.get("requires_python", "")
        result["keywords"] = (info.get("keywords") or "").split(",")[:10]

        # Project URLs
        project_urls = info.get("project_urls") or {}
        result["repository"] = project_urls.get("Source") or project_urls.get("Repository") or project_urls.get("GitHub") or ""
        result["documentation"] = project_urls.get("Documentation") or ""

    _set_cache(cache_key, result)
    return result


# --- GitHub -------------------------------------------------------------------

async def enrich_github(repo_url: str) -> dict[str, Any]:
    """Fetch GitHub repo data: stars, forks, last commit, issues."""
    cache_key = f"gh:{repo_url}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: dict[str, Any] = {"source": "github", "repo_url": repo_url}

    # Extract owner/repo from URL
    match = re.search(r"github\.com/([^/]+)/([^/\s.]+)", repo_url)
    if not match:
        return result

    owner, repo = match.group(1), match.group(2).rstrip(".git")
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    data = await _fetch_json(api_url)
    if data:
        result["stars"] = data.get("stargazers_count", 0)
        result["forks"] = data.get("forks_count", 0)
        result["open_issues"] = data.get("open_issues_count", 0)
        result["watchers"] = data.get("watchers_count", 0)
        result["language"] = data.get("language", "")
        result["license"] = ""
        lic = data.get("license")
        if isinstance(lic, dict):
            result["license"] = lic.get("spdx_id") or lic.get("name", "")
        result["created_at"] = data.get("created_at", "")
        result["updated_at"] = data.get("updated_at", "")
        result["pushed_at"] = data.get("pushed_at", "")
        result["archived"] = data.get("archived", False)
        result["description"] = data.get("description", "")
        result["topics"] = data.get("topics", [])
        result["default_branch"] = data.get("default_branch", "main")
        result["has_wiki"] = data.get("has_wiki", False)
        result["has_security_policy"] = False

        # Check for SECURITY.md (separate API call)
        sec = await _fetch_json(f"{api_url}/contents/SECURITY.md")
        if sec and sec.get("name"):
            result["has_security_policy"] = True

    _set_cache(cache_key, result)
    return result


# --- OSV.dev (Google's CVE database) -----------------------------------------

async def check_vulnerabilities(package_name: str, ecosystem: str = "npm") -> dict[str, Any]:
    """Check for known vulnerabilities using Google's OSV.dev API (free, no auth)."""
    cache_key = f"osv:{ecosystem}:{package_name}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result: dict[str, Any] = {
        "package": package_name,
        "ecosystem": ecosystem,
        "vulnerabilities": [],
        "total_vulns": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    data = await _post_json("https://api.osv.dev/v1/query", {
        "package": {"name": package_name, "ecosystem": ecosystem.upper() if ecosystem == "npm" else ecosystem},
    })

    if data and "vulns" in data:
        vulns = data["vulns"]
        result["total_vulns"] = len(vulns)

        for v in vulns[:20]:  # Cap at 20
            severity = "unknown"
            cvss_score = 0
            for s in v.get("severity", []):
                if s.get("type") == "CVSS_V3":
                    try:
                        # Extract base score from CVSS vector
                        score_str = s.get("score", "0")
                        cvss_score = float(score_str) if isinstance(score_str, (int, float, str)) else 0
                    except (ValueError, TypeError):
                        pass

            # Classify severity from database_specific or CVSS
            db_severity = v.get("database_specific", {}).get("severity", "").upper()
            if db_severity in ("CRITICAL",):
                severity = "critical"
                result["critical"] += 1
            elif db_severity in ("HIGH",) or cvss_score >= 7.0:
                severity = "high"
                result["high"] += 1
            elif db_severity in ("MODERATE", "MEDIUM") or cvss_score >= 4.0:
                severity = "medium"
                result["medium"] += 1
            else:
                severity = "low"
                result["low"] += 1

            result["vulnerabilities"].append({
                "id": v.get("id", ""),
                "summary": v.get("summary", "")[:200],
                "severity": severity,
                "published": v.get("published", ""),
                "aliases": v.get("aliases", [])[:3],
            })

    _set_cache(cache_key, result)
    return result


# --- Combined enrichment ------------------------------------------------------

async def enrich_tool(tool_data: dict[str, Any]) -> dict[str, Any]:
    """Enrich a tool with all available external data.

    Returns a dict with enrichment results from each source.
    """
    result: dict[str, Any] = {"enriched": True, "sources": []}

    name = tool_data.get("service_name", "") or tool_data.get("name", "")
    url = tool_data.get("url", "")
    tc = tool_data.get("type_config") or {}
    service_type = tool_data.get("service_type", "")

    tasks = []

    # npm enrichment
    npm_pkg = tc.get("npm_package") or ""
    if not npm_pkg and service_type in ("mcp_server", "cli_tool"):
        # Try to guess npm package name
        npm_pkg = name.lower().replace(" ", "-")
    if npm_pkg:
        tasks.append(("npm", enrich_npm(npm_pkg)))

    # GitHub enrichment
    github_url = ""
    cross_refs = tool_data.get("cross_refs", {})
    if cross_refs.get("github"):
        github_url = cross_refs["github"]
    elif "github.com" in url:
        github_url = url
    if github_url:
        tasks.append(("github", enrich_github(github_url)))

    # Vulnerability check
    if npm_pkg:
        tasks.append(("osv", check_vulnerabilities(npm_pkg, "npm")))

    # Run all enrichments concurrently
    if tasks:
        labels = [t[0] for t in tasks]
        coros = [t[1] for t in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

        for label, res in zip(labels, results):
            if isinstance(res, Exception):
                logger.warning("Enrichment %s failed: %s", label, res)
                continue
            result[label] = res
            result["sources"].append(label)

    return result
