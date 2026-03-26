#!/usr/bin/env python3
"""Merge all scan result files into a unified prebuilt-scans.json catalog.

Sources processed (in priority order — higher priority wins on duplicates):
1. data/prebuilt-scans.json      — full detailed scans (highest priority)
2. data/mcp-scan-results.json    — lightweight MCP endpoint scans
3. data/github-scan-results.json — GitHub repo scans
4. data/glama-scan-results.json  — Glama directory scans
5. data/all-agent-tools.json     — APIs/tools from apis.guru, n8n, composio
6. data/mcp-registry-all.json    — Official MCP registry entries
7. data/skills-cli-collected.json — npm/GitHub/Homebrew CLI tools & skills

Deduplication strategy:
- Normalize URLs: lowercase domain, strip trailing slash, strip fragments
- For duplicates by URL: keep the entry with the highest score
- For entries without a URL: use name-based dedup

Output:
- data/prebuilt-scans.json (overwrites)
- backend/data/prebuilt-scans.json (copy)
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------

def normalize_url(raw: str) -> str:
    """Lowercase domain, strip trailing slash, strip fragment, ensure scheme."""
    if not raw:
        return ""
    raw = raw.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    domain = parsed.netloc.lower().rstrip(".")
    path = parsed.path.rstrip("/")
    # Strip fragment, keep query
    normalized = urlunparse((
        parsed.scheme.lower(),
        domain,
        path,
        "",           # params
        parsed.query,
        "",           # fragment
    ))
    return normalized


def derive_name_from_url(url: str) -> str:
    """Extract a human-readable service name from a URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # GitHub repos: github.com/owner/repo -> "owner/repo"
    if "github.com" in domain:
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        elif len(parts) == 1 and parts[0]:
            return parts[0]
        return "github"

    # Strip common prefixes
    domain = re.sub(r"^(www\.|api\.|docs\.)", "", domain)
    # Use domain without TLD as name
    name_part = domain.split(".")[0] if "." in domain else domain
    return name_part.replace("-", " ").replace("_", " ").title()


def make_scan_id(url: str, name: str) -> str:
    """Generate a deterministic scan_id from URL or name."""
    seed = url or name
    h = hashlib.md5(seed.encode()).hexdigest()[:12]
    return f"scn_{h}"


# ---------------------------------------------------------------------------
# Rating from score
# ---------------------------------------------------------------------------

def score_to_rating(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Strong"
    if score >= 50:
        return "Moderate"
    if score >= 30:
        return "Basic"
    return "Low"


# ---------------------------------------------------------------------------
# Category inference
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ai": ["ai", "llm", "gpt", "claude", "openai", "ml", "model", "embedding",
            "inference", "neural", "diffusion", "stable", "midjourney", "replicate",
            "hugging", "anthropic", "groq", "together", "cohere", "mistral"],
    "developer_tools": ["github", "git", "docker", "ci", "deploy", "dev", "sdk",
                        "test", "debug", "lint", "build", "npm", "pip", "cargo",
                        "vercel", "netlify", "supabase", "firebase", "sentry"],
    "communication": ["slack", "discord", "email", "chat", "message", "telegram",
                      "whatsapp", "notification", "sms", "twilio", "sendgrid"],
    "data": ["database", "sql", "analytics", "data", "postgres", "mongo",
             "redis", "elastic", "snowflake", "bigquery", "warehouse"],
    "productivity": ["notion", "calendar", "task", "project", "todo", "workflow",
                     "automat", "zapier", "n8n", "make", "airtable", "clickup"],
    "blockchain": ["solana", "ethereum", "web3", "crypto", "defi", "nft",
                   "blockchain", "token", "wallet", "smart contract", "dapp"],
    "payments": ["payment", "stripe", "billing", "invoice", "checkout",
                 "paypal", "subscription", "commerce"],
    "mcp": ["mcp", "model context protocol"],
    "search": ["search", "algolia", "elasticsearch", "typesense", "meilisearch"],
    "storage": ["storage", "s3", "blob", "file", "upload", "cloud storage"],
    "cms": ["cms", "content management", "wordpress", "sanity", "strapi"],
    "security": ["security", "auth", "oauth", "encryption", "vault", "secret"],
    "monitoring": ["monitor", "observ", "logging", "metrics", "apm", "tracing"],
}


def infer_category(name: str, description: str, existing: str = "") -> str:
    """Infer a category from name + description text."""
    if existing and existing != "other" and existing != "":
        return existing
    combined = f"{name} {description}".lower()
    best_cat = "other"
    best_hits = 0
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        hits = sum(1 for k in keywords if k in combined)
        if hits > best_hits:
            best_hits = hits
            best_cat = cat
    return best_cat


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------

def load_prebuilt_scans() -> list[dict[str, Any]]:
    """Load existing prebuilt-scans.json (full detailed scans)."""
    path = DATA / "prebuilt-scans.json"
    if not path.exists():
        return []
    with open(path) as f:
        items = json.load(f)
    results = []
    for item in items:
        entry = {
            "scan_id": item.get("scan_id", ""),
            "url": item.get("url", ""),
            "service_name": item.get("service_name", ""),
            "clarvia_score": item.get("clarvia_score", 0),
            "rating": item.get("rating", ""),
            "category": item.get("category", "other"),
            "description": item.get("description", ""),
            "service_type": item.get("service_type", "general"),
            "source_file": "prebuilt-scans",
            # Preserve full details
            "dimensions": item.get("dimensions"),
            "onchain_bonus": item.get("onchain_bonus"),
            "top_recommendations": item.get("top_recommendations"),
            "scanned_at": item.get("scanned_at"),
            "scan_duration_ms": item.get("scan_duration_ms"),
        }
        results.append(entry)
    return results


def load_scan_results(filename: str, source_label: str) -> list[dict[str, Any]]:
    """Load lightweight scan results (mcp/github/glama)."""
    path = DATA / filename
    if not path.exists():
        print(f"  [SKIP] {filename} not found")
        return []
    with open(path) as f:
        items = json.load(f)

    results = []
    for item in items:
        if not item.get("ok", True):
            continue  # Skip failed scans

        url = item.get("url", "")
        raw_name = item.get("service_name", "")

        # Fix generic "Github" names from github/glama scan results
        if raw_name.lower() == "github" and url:
            raw_name = derive_name_from_url(url)

        score = item.get("score", 0) or item.get("clarvia_score", 0)

        entry = {
            "scan_id": item.get("scan_id", make_scan_id(url, raw_name)),
            "url": url,
            "service_name": raw_name,
            "clarvia_score": score,
            "rating": item.get("rating", score_to_rating(score)),
            "category": "other",
            "description": "",
            "service_type": "general",
            "source_file": source_label,
        }
        results.append(entry)
    return results


def load_all_agent_tools() -> list[dict[str, Any]]:
    """Load all-agent-tools.json (APIs from apis.guru, n8n, composio, etc.)."""
    path = DATA / "all-agent-tools.json"
    if not path.exists():
        return []
    with open(path) as f:
        items = json.load(f)

    results = []
    for item in items:
        name = item.get("name") or item.get("title") or ""
        desc = item.get("description") or ""
        url = item.get("homepage") or item.get("url") or ""
        category = item.get("category", "other")
        source = item.get("source", "unknown")
        tool_type = item.get("type", "api")

        # Score based on metadata richness
        score = 0
        if desc and len(desc) > 10:
            score += 15
        if len(desc) > 50:
            score += 5
        if len(desc) > 100:
            score += 5
        if url:
            score += 5
        if item.get("openapi_url"):
            score += 10
        if item.get("version") and item["version"] != "0.0.0":
            score += 5
        # Source-based bonus
        source_bonus = {"apis_guru": 15, "n8n": 12, "composio": 12}.get(source, 5)
        score += source_bonus
        score = min(score, 60)  # Cap for unscanned tools

        type_map = {"api": "api", "mcp_server": "mcp_server", "connector": "api"}
        service_type = type_map.get(tool_type, "api")

        entry = {
            "scan_id": make_scan_id(url, name),
            "url": url,
            "service_name": name or derive_name_from_url(url),
            "clarvia_score": score,
            "rating": score_to_rating(score),
            "category": infer_category(name, desc, category),
            "description": desc[:300],
            "service_type": service_type,
            "source_file": "all-agent-tools",
        }
        results.append(entry)
    return results


def load_mcp_registry() -> list[dict[str, Any]]:
    """Load mcp-registry-all.json (official MCP registry)."""
    path = DATA / "mcp-registry-all.json"
    if not path.exists():
        return []
    with open(path) as f:
        items = json.load(f)

    results = []
    for item in items:
        server = item.get("server", {})
        name = server.get("name") or server.get("title") or ""
        desc = server.get("description") or ""
        url = server.get("websiteUrl") or ""
        repo = server.get("repository", {})
        repo_url = repo.get("url", "") if isinstance(repo, dict) else ""
        if not url and repo_url:
            url = repo_url
        version = server.get("version", "")

        # Score based on metadata
        score = 20  # Base score for being in the official registry
        if desc and len(desc) > 10:
            score += 10
        if len(desc) > 50:
            score += 5
        if url:
            score += 5
        if version and version != "0.0.0":
            score += 5
            parts = version.split(".")
            if parts[0].isdigit() and int(parts[0]) >= 1:
                score += 5
        if server.get("remotes"):
            score += 5  # Has live endpoints
        score = min(score, 55)  # Cap for unscanned

        entry = {
            "scan_id": make_scan_id(url, name),
            "url": url,
            "service_name": name or derive_name_from_url(url),
            "clarvia_score": score,
            "rating": score_to_rating(score),
            "category": infer_category(name, desc, "mcp"),
            "description": desc[:300],
            "service_type": "mcp_server",
            "source_file": "mcp-registry",
        }
        results.append(entry)
    return results


def load_skills_cli() -> list[dict[str, Any]]:
    """Load skills-cli-collected.json (npm/GitHub/Homebrew tools)."""
    path = DATA / "skills-cli-collected.json"
    if not path.exists():
        return []
    with open(path) as f:
        items = json.load(f)

    results = []
    for item in items:
        name = item.get("name") or ""
        desc = item.get("description") or ""
        url = item.get("homepage") or item.get("url") or item.get("npm_url") or ""
        repo = item.get("repository") or ""
        if isinstance(repo, dict):
            repo = repo.get("url", "")
        if not url and repo:
            url = repo
        version = item.get("version", "")
        npm_score = item.get("score", 0) or 0
        source = item.get("source", "unknown")
        tool_type = item.get("type", "cli_tool")
        keywords = item.get("keywords") or []

        # Score based on metadata richness
        score = 10  # Base
        if desc and len(desc) > 10:
            score += 5
        if len(desc) > 50:
            score += 5
        if url:
            score += 3
        if version and version != "0.0.0":
            score += 3
            parts = version.split(".")
            if parts and parts[0].isdigit() and int(parts[0]) >= 1:
                score += 3
        if keywords and len(keywords) >= 2:
            score += 2
        # npm popularity signal
        if isinstance(npm_score, (int, float)):
            if npm_score > 5000:
                score += 10
            elif npm_score > 1000:
                score += 7
            elif npm_score > 100:
                score += 4
            elif npm_score > 10:
                score += 2
        if item.get("install_command"):
            score += 3
        score = min(score, 50)  # Cap for unscanned

        type_map = {"cli_tool": "cli_tool", "skill": "skill"}
        service_type = type_map.get(tool_type, "cli_tool")

        entry = {
            "scan_id": make_scan_id(url, name),
            "url": url,
            "service_name": name or derive_name_from_url(url),
            "clarvia_score": score,
            "rating": score_to_rating(score),
            "category": infer_category(name, desc),
            "description": desc[:300],
            "service_type": service_type,
            "source_file": "skills-cli",
        }
        results.append(entry)
    return results


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def merge_all() -> list[dict[str, Any]]:
    """Merge all sources, deduplicate by normalized URL."""
    print("=" * 60)
    print("CLARVIA CATALOG MERGE")
    print("=" * 60)

    # Load all sources (order matters — earlier sources get priority)
    sources = [
        ("prebuilt-scans", load_prebuilt_scans),
        ("mcp-scan-results", lambda: load_scan_results("mcp-scan-results.json", "mcp-scan")),
        ("github-scan-results", lambda: load_scan_results("github-scan-results.json", "github-scan")),
        ("glama-scan-results", lambda: load_scan_results("glama-scan-results.json", "glama-scan")),
        ("all-agent-tools", load_all_agent_tools),
        ("mcp-registry-all", load_mcp_registry),
        ("skills-cli-collected", load_skills_cli),
    ]

    all_entries: list[tuple[str, dict[str, Any]]] = []
    source_counts = Counter()

    for label, loader in sources:
        print(f"\nLoading {label}...")
        items = loader()
        print(f"  -> {len(items)} entries")
        source_counts[label] = len(items)
        for item in items:
            all_entries.append((label, item))

    total_raw = len(all_entries)
    print(f"\nTotal raw entries: {total_raw}")

    # Deduplicate by normalized URL (highest score wins)
    url_map: dict[str, dict[str, Any]] = {}  # normalized_url -> best entry
    name_map: dict[str, dict[str, Any]] = {}  # lowercase name -> best entry (for no-url items)
    dupes_removed = 0
    no_url_count = 0

    for label, entry in all_entries:
        url = normalize_url(entry.get("url", ""))
        score = entry.get("clarvia_score", 0)

        if url:
            if url in url_map:
                existing = url_map[url]
                if score > existing.get("clarvia_score", 0):
                    # New entry has higher score — replace but preserve detail fields
                    if existing.get("dimensions") and not entry.get("dimensions"):
                        entry["dimensions"] = existing["dimensions"]
                    if existing.get("top_recommendations") and not entry.get("top_recommendations"):
                        entry["top_recommendations"] = existing["top_recommendations"]
                    if existing.get("scanned_at") and not entry.get("scanned_at"):
                        entry["scanned_at"] = existing["scanned_at"]
                    if existing.get("description") and not entry.get("description"):
                        entry["description"] = existing["description"]
                    url_map[url] = entry
                else:
                    # Existing wins, but still merge metadata from new
                    if entry.get("description") and not existing.get("description"):
                        existing["description"] = entry["description"]
                    if entry.get("category") != "other" and existing.get("category") == "other":
                        existing["category"] = entry["category"]
                dupes_removed += 1
            else:
                url_map[url] = entry
        else:
            # No URL — deduplicate by name
            no_url_count += 1
            name_key = entry.get("service_name", "").lower().strip()
            if not name_key:
                continue
            if name_key in name_map:
                existing = name_map[name_key]
                if score > existing.get("clarvia_score", 0):
                    name_map[name_key] = entry
                dupes_removed += 1
            else:
                name_map[name_key] = entry

    # Combine URL-deduped and name-deduped entries
    merged = list(url_map.values()) + list(name_map.values())

    # Clean up output: remove internal tracking fields, ensure schema consistency
    output = []
    for entry in merged:
        clean = {
            "scan_id": entry.get("scan_id", make_scan_id(entry.get("url", ""), entry.get("service_name", ""))),
            "url": entry.get("url", ""),
            "service_name": entry.get("service_name", "Unknown"),
            "clarvia_score": entry.get("clarvia_score", 0),
            "rating": entry.get("rating", score_to_rating(entry.get("clarvia_score", 0))),
            "category": entry.get("category", "other"),
            "description": entry.get("description", ""),
            "service_type": entry.get("service_type", "general"),
        }
        # Preserve detailed fields if present (from full scans)
        if entry.get("dimensions"):
            clean["dimensions"] = entry["dimensions"]
        if entry.get("onchain_bonus") is not None:
            clean["onchain_bonus"] = entry["onchain_bonus"]
        if entry.get("top_recommendations"):
            clean["top_recommendations"] = entry["top_recommendations"]
        if entry.get("scanned_at"):
            clean["scanned_at"] = entry["scanned_at"]
        if entry.get("scan_duration_ms"):
            clean["scan_duration_ms"] = entry["scan_duration_ms"]

        output.append(clean)

    # Sort: highest score first
    output.sort(key=lambda x: (-x["clarvia_score"], x["service_name"].lower()))

    # Stats
    print("\n" + "=" * 60)
    print("MERGE RESULTS")
    print("=" * 60)
    print(f"\nRaw entries loaded:    {total_raw:>8,}")
    print(f"Duplicates removed:   {dupes_removed:>8,}")
    print(f"Entries without URL:  {no_url_count:>8,}")
    print(f"Final catalog size:   {len(output):>8,}")

    print(f"\n--- By source file ---")
    for label, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {label:<30s} {count:>6,}")

    print(f"\n--- By category ---")
    cat_counts = Counter(e["category"] for e in output)
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:<30s} {count:>6,}")

    print(f"\n--- By service type ---")
    type_counts = Counter(e["service_type"] for e in output)
    for st, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {st:<30s} {count:>6,}")

    print(f"\n--- Score distribution ---")
    score_dist = {
        "Excellent (90+)": len([e for e in output if e["clarvia_score"] >= 90]),
        "Strong (75-89)": len([e for e in output if 75 <= e["clarvia_score"] < 90]),
        "Moderate (50-74)": len([e for e in output if 50 <= e["clarvia_score"] < 75]),
        "Basic (30-49)": len([e for e in output if 30 <= e["clarvia_score"] < 49]),
        "Low (<30)": len([e for e in output if e["clarvia_score"] < 30]),
    }
    for label, count in score_dist.items():
        print(f"  {label:<30s} {count:>6,}")

    return output


def main():
    output = merge_all()

    # Write to data/prebuilt-scans.json
    out_path = DATA / "prebuilt-scans.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nWritten: {out_path} ({len(output):,} entries)")

    # Copy to backend/data/prebuilt-scans.json
    backend_path = ROOT / "backend" / "data" / "prebuilt-scans.json"
    if backend_path.parent.exists():
        shutil.copy2(out_path, backend_path)
        print(f"Copied:  {backend_path}")

    # Also copy to frontend/public/data/prebuilt-scans.json if it exists
    frontend_path = ROOT / "frontend" / "public" / "data" / "prebuilt-scans.json"
    if frontend_path.parent.exists():
        shutil.copy2(out_path, frontend_path)
        print(f"Copied:  {frontend_path}")

    # Verify JSON validity
    with open(out_path) as f:
        verify = json.load(f)
    assert len(verify) == len(output), "Verification failed: item count mismatch"
    assert all("scan_id" in e for e in verify), "Verification failed: missing scan_id"
    assert all("url" in e for e in verify), "Verification failed: missing url"
    assert all("clarvia_score" in e for e in verify), "Verification failed: missing clarvia_score"
    print(f"\nVerification PASSED: {len(verify):,} valid entries")


if __name__ == "__main__":
    main()
