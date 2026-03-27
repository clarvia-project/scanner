#!/usr/bin/env python3
"""GitHub SKILL.md Crawler for Clarvia.

Discovers agent skills by searching GitHub for SKILL.md files and known
skill repositories. Parses YAML frontmatter to extract metadata.

Sources:
  - GitHub Code Search: filename:SKILL.md
  - GitHub Topic Search: agent-skills, claude-skills, codex-skills
  - GitHub directory search: repos with .claude/skills/
  - Official repos: anthropics/skills, openai/skills
  - SkillsMP API (skillsmp.com) if available

Usage:
    python scripts/automation/crawlers/skills_crawler.py [--dry-run]
"""

import argparse
import asyncio
import base64
import json
import logging
import re
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base import (
    GITHUB_TOKEN,
    RateLimiter,
    normalize_tool,
    load_known_urls,
    dedup_discoveries,
    save_discoveries,
    fetch_json,
    fetch_text,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# GitHub rate limiter — 1.5s between requests to stay well within limits
GH_RATE_LIMITER = RateLimiter(delay=1.5, name="github")

# GitHub API base
GH_API = "https://api.github.com"

# GitHub Code Search queries for SKILL.md files
CODE_SEARCH_QUERIES = [
    "filename:SKILL.md",
    "filename:SKILL.md path:.claude/skills",
    "filename:SKILL.md path:skills",
]

# GitHub topic searches
TOPIC_SEARCHES = [
    "agent-skills",
    "claude-skills",
    "codex-skills",
    "ai-agent-skills",
    "mcp-skills",
    "claude-code-skills",
]

# Known official skill repositories to crawl directly
OFFICIAL_REPOS = [
    "anthropics/skills",
    "openai/skills",
    "anthropics/claude-code-skills",
]

# SkillsMP API endpoint (best-effort, may not exist)
SKILLSMP_API = "https://skillsmp.com/api/skills"


def _gh_headers() -> dict:
    """Build GitHub API headers with auth token if available."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def parse_skill_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from a SKILL.md file.

    Returns a dict with extracted fields: name, description, license,
    compatibility, author, version, and the raw body text.
    """
    result = {
        "name": "",
        "description": "",
        "license": "",
        "compatibility": [],
        "author": "",
        "version": "",
        "body": "",
    }

    # Split frontmatter from body
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', content, re.DOTALL)
    if not fm_match:
        # No frontmatter — treat the whole thing as body, try to extract name
        result["body"] = content.strip()
        # Use first heading as name
        heading = re.match(r'^#\s+(.+)', content.strip())
        if heading:
            result["name"] = heading.group(1).strip()
        return result

    frontmatter_text = fm_match.group(1)
    result["body"] = fm_match.group(2).strip()

    # Simple YAML-like parsing (avoid heavy yaml dependency)
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        kv = re.match(r'^(\w[\w.-]*)\s*:\s*(.+)', line)
        if not kv:
            continue

        key = kv.group(1).lower().strip()
        value = kv.group(2).strip().strip('"').strip("'")

        if key == "name":
            result["name"] = value
        elif key == "description":
            result["description"] = value
        elif key == "license":
            result["license"] = value
        elif key == "author":
            result["author"] = value
        elif key == "version":
            result["version"] = value
        elif key in ("compatibility", "compatible_with", "platforms"):
            # Could be comma-separated or YAML list
            result["compatibility"] = [
                v.strip().strip("-").strip()
                for v in re.split(r'[,\n]', value)
                if v.strip()
            ]

    return result


async def search_github_code(
    session: aiohttp.ClientSession,
    query: str,
    max_pages: int = 5,
) -> list[dict]:
    """Search GitHub Code Search API for files matching query.

    Returns list of dicts with repo info and file paths.
    """
    results = []
    headers = _gh_headers()

    for page in range(1, max_pages + 1):
        url = f"{GH_API}/search/code?q={query}&per_page=100&page={page}"
        data = await fetch_json(
            session, url, headers=headers, rate_limiter=GH_RATE_LIMITER
        )
        if not data:
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            repo = item.get("repository", {})
            results.append({
                "file_path": item.get("path", ""),
                "file_url": item.get("html_url", ""),
                "repo_full_name": repo.get("full_name", ""),
                "repo_url": repo.get("html_url", ""),
                "repo_description": repo.get("description") or "",
                "repo_private": repo.get("private", False),
            })

        total = data.get("total_count", 0)
        if page * 100 >= total:
            break

        logger.info(
            "  Code search '%s' page %d: %d items (total: %d)",
            query, page, len(items), total,
        )

    return results


async def search_github_topics(
    session: aiohttp.ClientSession,
    topic: str,
    max_pages: int = 3,
) -> list[dict]:
    """Search GitHub repos by topic."""
    results = []
    headers = _gh_headers()

    for page in range(1, max_pages + 1):
        url = f"{GH_API}/search/repositories?q=topic:{topic}&sort=stars&order=desc&per_page=100&page={page}"
        data = await fetch_json(
            session, url, headers=headers, rate_limiter=GH_RATE_LIMITER
        )
        if not data:
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            results.append({
                "repo_full_name": item.get("full_name", ""),
                "repo_url": item.get("html_url", ""),
                "repo_description": item.get("description") or "",
                "stars": item.get("stargazers_count", 0),
                "updated_at": item.get("updated_at", ""),
                "owner": item.get("owner", {}).get("login", ""),
                "topics": item.get("topics", []),
            })

        total = data.get("total_count", 0)
        if page * 100 >= total:
            break

    return results


async def fetch_file_content(
    session: aiohttp.ClientSession,
    repo_full_name: str,
    file_path: str,
) -> str | None:
    """Fetch raw file content from a GitHub repo."""
    headers = _gh_headers()
    url = f"{GH_API}/repos/{repo_full_name}/contents/{file_path}"
    data = await fetch_json(
        session, url, headers=headers, rate_limiter=GH_RATE_LIMITER
    )
    if not data:
        return None

    # GitHub returns base64-encoded content
    encoding = data.get("encoding", "")
    content = data.get("content", "")

    if encoding == "base64" and content:
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning("Failed to decode content for %s/%s: %s", repo_full_name, file_path, e)
            return None

    # If too large, try download_url
    download_url = data.get("download_url")
    if download_url:
        return await fetch_text(
            session, download_url, headers=headers, rate_limiter=GH_RATE_LIMITER
        )

    return None


async def fetch_repo_info(
    session: aiohttp.ClientSession,
    repo_full_name: str,
) -> dict | None:
    """Fetch repository metadata (stars, owner, updated_at)."""
    headers = _gh_headers()
    url = f"{GH_API}/repos/{repo_full_name}"
    data = await fetch_json(
        session, url, headers=headers, rate_limiter=GH_RATE_LIMITER
    )
    if not data:
        return None

    return {
        "stars": data.get("stargazers_count", 0),
        "owner": data.get("owner", {}).get("login", ""),
        "updated_at": data.get("updated_at", ""),
        "description": data.get("description") or "",
        "topics": data.get("topics", []),
        "license": (data.get("license") or {}).get("spdx_id", ""),
    }


async def list_directory_contents(
    session: aiohttp.ClientSession,
    repo_full_name: str,
    path: str,
) -> list[dict]:
    """List files in a GitHub repo directory."""
    headers = _gh_headers()
    url = f"{GH_API}/repos/{repo_full_name}/contents/{path}"
    data = await fetch_json(
        session, url, headers=headers, rate_limiter=GH_RATE_LIMITER
    )
    if not data or not isinstance(data, list):
        return []
    return data


async def crawl_code_search(session: aiohttp.ClientSession) -> list[dict]:
    """Discover SKILL.md files via GitHub Code Search."""
    all_files = {}  # keyed by repo_full_name/file_path to dedup

    for query in CODE_SEARCH_QUERIES:
        logger.info("GitHub code search: '%s'", query)
        results = await search_github_code(session, query)
        for r in results:
            key = f"{r['repo_full_name']}/{r['file_path']}"
            if key not in all_files:
                all_files[key] = r
        logger.info("  '%s': %d results (unique total: %d)", query, len(results), len(all_files))

    logger.info("Code search total unique SKILL.md files: %d", len(all_files))
    return list(all_files.values())


async def crawl_topic_repos(session: aiohttp.ClientSession) -> list[dict]:
    """Discover skill repos via GitHub topic search."""
    all_repos = {}  # keyed by repo_full_name

    for topic in TOPIC_SEARCHES:
        logger.info("GitHub topic search: '%s'", topic)
        results = await search_github_topics(session, topic)
        for r in results:
            name = r["repo_full_name"]
            if name not in all_repos:
                all_repos[name] = r
        logger.info("  '%s': %d results (unique total: %d)", topic, len(results), len(all_repos))

    logger.info("Topic search total unique repos: %d", len(all_repos))
    return list(all_repos.values())


async def crawl_official_repo(
    session: aiohttp.ClientSession,
    repo_full_name: str,
) -> list[dict]:
    """Crawl a known official skills repository for SKILL.md files.

    Walks the repo directory tree looking for SKILL.md files.
    """
    discoveries = []
    logger.info("Crawling official repo: %s", repo_full_name)

    repo_info = await fetch_repo_info(session, repo_full_name)
    if not repo_info:
        logger.warning("  Repo not found or inaccessible: %s", repo_full_name)
        return []

    # Try common skill directory locations
    skill_dirs = [
        "",        # root
        "skills",
        ".claude/skills",
    ]

    for skill_dir in skill_dirs:
        items = await list_directory_contents(session, repo_full_name, skill_dir)
        for item in items:
            name = item.get("name", "")
            item_type = item.get("type", "")

            # If it's a SKILL.md file directly
            if name.upper() == "SKILL.MD" and item_type == "file":
                content = await fetch_file_content(
                    session, repo_full_name, item.get("path", "")
                )
                if content:
                    parsed = parse_skill_frontmatter(content)
                    skill_name = parsed["name"] or name.replace(".md", "")
                    discoveries.append({
                        "skill_name": skill_name,
                        "repo_full_name": repo_full_name,
                        "file_path": item.get("path", ""),
                        "parsed": parsed,
                        "repo_info": repo_info,
                    })

            # If it's a directory, look for SKILL.md inside
            elif item_type == "dir":
                sub_items = await list_directory_contents(
                    session, repo_full_name, item.get("path", "")
                )
                for sub in sub_items:
                    if sub.get("name", "").upper() == "SKILL.MD" and sub.get("type") == "file":
                        content = await fetch_file_content(
                            session, repo_full_name, sub.get("path", "")
                        )
                        if content:
                            parsed = parse_skill_frontmatter(content)
                            skill_name = parsed["name"] or item.get("name", "")
                            discoveries.append({
                                "skill_name": skill_name,
                                "repo_full_name": repo_full_name,
                                "file_path": sub.get("path", ""),
                                "parsed": parsed,
                                "repo_info": repo_info,
                            })

    logger.info("  Official repo %s: %d skills found", repo_full_name, len(discoveries))
    return discoveries


async def crawl_skillsmp_api(session: aiohttp.ClientSession) -> list[dict]:
    """Attempt to crawl SkillsMP API for skill listings (best-effort)."""
    discoveries = []
    logger.info("Checking SkillsMP API: %s", SKILLSMP_API)

    rate_limiter = RateLimiter(delay=1.0, name="skillsmp")

    # Try paginated list
    for page in range(1, 6):
        url = f"{SKILLSMP_API}?page={page}&per_page=100"
        data = await fetch_json(session, url, rate_limiter=rate_limiter)
        if not data:
            logger.info("  SkillsMP API not available or returned no data")
            break

        items = data if isinstance(data, list) else data.get("skills", data.get("items", data.get("data", [])))
        if not items or not isinstance(items, list):
            break

        for item in items:
            if isinstance(item, dict):
                discoveries.append({
                    "skill_name": item.get("name", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", item.get("github_url", item.get("repo_url", ""))),
                    "author": item.get("author", item.get("owner", "")),
                    "source": "skillsmp",
                })

        logger.info("  SkillsMP page %d: %d items", page, len(items))

        # If fewer results than page size, we've reached the end
        if len(items) < 100:
            break

    logger.info("SkillsMP total: %d skills", len(discoveries))
    return discoveries


def _normalize_skill_discovery(
    skill_data: dict,
    source_label: str = "github_skills",
) -> dict | None:
    """Convert a raw skill discovery dict to the normalized Clarvia schema."""
    # Determine the best URL
    repo_name = skill_data.get("repo_full_name", "")
    url = skill_data.get("url", "")
    if not url and repo_name:
        url = f"https://github.com/{repo_name}"

    if not url:
        return None

    parsed = skill_data.get("parsed", {})
    repo_info = skill_data.get("repo_info", {})

    # Determine skill name
    name = (
        parsed.get("name")
        or skill_data.get("skill_name")
        or skill_data.get("name")
        or repo_name.split("/")[-1] if repo_name else ""
    )
    if not name:
        return None

    description = (
        parsed.get("description")
        or skill_data.get("description")
        or skill_data.get("repo_description", "")
        or repo_info.get("description", "")
    )

    extra = {
        "skill_name": name,
        "skill_format": "SKILL.md",
        "repo_owner": repo_info.get("owner") or skill_data.get("owner", ""),
        "repo_stars": repo_info.get("stars", skill_data.get("stars", 0)),
        "last_updated": repo_info.get("updated_at") or skill_data.get("updated_at", ""),
        "file_path": skill_data.get("file_path", ""),
    }

    # Add optional metadata from frontmatter
    if parsed.get("author"):
        extra["author"] = parsed["author"]
    if parsed.get("version"):
        extra["version"] = parsed["version"]
    if parsed.get("license") or repo_info.get("license"):
        extra["license"] = parsed.get("license") or repo_info.get("license", "")
    if parsed.get("compatibility"):
        extra["compatibility"] = parsed["compatibility"]

    return normalize_tool(
        name=name,
        url=url,
        description=description,
        source=source_label,
        category="skills",
        extra=extra,
    )


async def crawl_skills(session: aiohttp.ClientSession) -> list[dict]:
    """Main crawl orchestrator — runs all skill discovery methods."""
    discoveries = []
    seen_repos = set()  # Track repos already processed to avoid redundant API calls

    # 1. GitHub Code Search for SKILL.md files
    logger.info("=== Phase 1: GitHub Code Search ===")
    code_results = await crawl_code_search(session)

    for file_info in code_results:
        repo_name = file_info["repo_full_name"]
        if repo_name in seen_repos:
            continue

        # Fetch the SKILL.md content and parse it
        content = await fetch_file_content(
            session, repo_name, file_info["file_path"]
        )
        if not content:
            continue

        parsed = parse_skill_frontmatter(content)

        # Fetch repo info for stars/metadata
        repo_info = await fetch_repo_info(session, repo_name)
        if not repo_info:
            repo_info = {}

        seen_repos.add(repo_name)

        entry = _normalize_skill_discovery({
            "repo_full_name": repo_name,
            "file_path": file_info["file_path"],
            "parsed": parsed,
            "repo_info": repo_info,
            "repo_description": file_info.get("repo_description", ""),
        })
        if entry:
            discoveries.append(entry)

    logger.info("Phase 1 complete: %d skills from code search", len(discoveries))

    # 2. GitHub Topic Search
    logger.info("=== Phase 2: GitHub Topic Search ===")
    topic_repos = await crawl_topic_repos(session)
    topic_count = 0

    for repo in topic_repos:
        repo_name = repo["repo_full_name"]
        if repo_name in seen_repos:
            continue
        seen_repos.add(repo_name)

        # Check if this repo has SKILL.md files
        for check_path in ["SKILL.md", "skills/SKILL.md", ".claude/skills"]:
            content = await fetch_file_content(session, repo_name, check_path)
            if content and check_path.endswith(".md"):
                parsed = parse_skill_frontmatter(content)
                entry = _normalize_skill_discovery({
                    "repo_full_name": repo_name,
                    "file_path": check_path,
                    "parsed": parsed,
                    "repo_info": repo,
                })
                if entry:
                    discoveries.append(entry)
                    topic_count += 1
                break
            elif not content and check_path == ".claude/skills":
                # Try to list the directory for SKILL.md files
                items = await list_directory_contents(session, repo_name, check_path)
                for item in items:
                    if item.get("type") == "dir":
                        sub_items = await list_directory_contents(
                            session, repo_name, item.get("path", "")
                        )
                        for sub in sub_items:
                            if sub.get("name", "").upper() == "SKILL.MD":
                                sub_content = await fetch_file_content(
                                    session, repo_name, sub.get("path", "")
                                )
                                if sub_content:
                                    parsed = parse_skill_frontmatter(sub_content)
                                    entry = _normalize_skill_discovery({
                                        "repo_full_name": repo_name,
                                        "file_path": sub.get("path", ""),
                                        "parsed": parsed,
                                        "repo_info": repo,
                                        "skill_name": item.get("name", ""),
                                    })
                                    if entry:
                                        discoveries.append(entry)
                                        topic_count += 1

    logger.info("Phase 2 complete: %d new skills from topic search", topic_count)

    # 3. Official repositories
    logger.info("=== Phase 3: Official Repositories ===")
    official_count = 0
    for repo_name in OFFICIAL_REPOS:
        if repo_name in seen_repos:
            continue
        seen_repos.add(repo_name)

        official_skills = await crawl_official_repo(session, repo_name)
        for skill in official_skills:
            entry = _normalize_skill_discovery(skill)
            if entry:
                discoveries.append(entry)
                official_count += 1

    logger.info("Phase 3 complete: %d skills from official repos", official_count)

    # 4. SkillsMP API (best-effort)
    logger.info("=== Phase 4: SkillsMP API ===")
    skillsmp_results = await crawl_skillsmp_api(session)
    skillsmp_count = 0
    for skill in skillsmp_results:
        if not skill.get("url"):
            continue
        entry = _normalize_skill_discovery(skill, source_label="skillsmp")
        if entry:
            discoveries.append(entry)
            skillsmp_count += 1

    logger.info("Phase 4 complete: %d skills from SkillsMP", skillsmp_count)

    logger.info(
        "Skills crawl total: %d discoveries (code=%d, topic=%d, official=%d, skillsmp=%d)",
        len(discoveries),
        len(discoveries) - topic_count - official_count - skillsmp_count,
        topic_count,
        official_count,
        skillsmp_count,
    )

    return discoveries


async def run(dry_run: bool = False) -> dict:
    """Entry point for crawl_all.py orchestration."""
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_skills(session)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "github_skills",
        "total_found": len(discoveries),
        "new_unique": len(unique),
        "duplicates_skipped": len(discoveries) - len(unique),
    }

    if not dry_run:
        saved = save_discoveries(unique)
        stats["queued"] = saved
    else:
        stats["dry_run"] = True
        for d in unique[:5]:
            logger.info("  [NEW] %s — %s", d["name"], d["url"])
        if len(unique) > 5:
            logger.info("  ... and %d more", len(unique) - 5)

    return stats


def main():
    parser = argparse.ArgumentParser(description="GitHub SKILL.md Crawler for Clarvia")
    parser.add_argument("--dry-run", action="store_true", help="Discover but don't queue")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
