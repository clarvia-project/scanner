#!/usr/bin/env python3
"""Batch Metadata Scoring Pipeline for Clarvia.

Reads tools from new-tools-queue.jsonl, scores them using Tier 1 metadata
scoring (0-100), deduplicates, and writes scored results to prebuilt-scans.json
for the Index API to serve.

Tier 1 scoring uses the legacy tool_scorer which handles flat metadata entries:
  - Description quality (0-20)
  - Documentation signals (0-20)
  - Ecosystem presence (0-20)
  - Agent compatibility (0-25)
  - Metadata quality / trust (0-15)

Usage:
    python scripts/batch_score.py                  # Full run
    python scripts/batch_score.py --limit 100      # Test with 100 tools
    python scripts/batch_score.py --dry-run         # Score but don't write
    python scripts/batch_score.py --min-score 20    # Only keep score >= 20
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

# Add project root to path so we can import scoring modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.tool_scorer import (
    score_tool as legacy_score,
    detect_pricing,
    extract_capabilities,
    detect_difficulty,
    estimate_popularity,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("batch_score")

# Paths
DATA_DIR = PROJECT_ROOT / "data"
QUEUE_FILE = DATA_DIR / "new-tools-queue.jsonl"
OUTPUT_FILE = PROJECT_ROOT / "backend" / "data" / "prebuilt-scans.json"
DB_FILE = PROJECT_ROOT / "backend" / "data" / "clarvia.db"


# ---------------------------------------------------------------------------
# Category classification (simplified from index_routes._classify)
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ai": ["ai", "llm", "gpt", "claude", "openai", "machine learning",
           "neural", "embedding", "vector", "transformer", "model",
           "anthropic", "gemini", "copilot", "whisper", "diffusion",
           "langchain", "llamaindex", "huggingface", "replicate", "groq"],
    "developer_tools": ["github", "git", "docker", "ci", "deploy", "dev",
                        "sdk", "framework", "compiler", "linter", "debugger",
                        "npm", "pip", "cargo", "build", "test", "debug",
                        "code", "ide", "editor", "vscode"],
    "communication": ["slack", "discord", "email", "chat", "message",
                      "notification", "sms", "messaging", "telegram",
                      "whatsapp", "twilio", "sendgrid"],
    "data": ["database", "sql", "analytics", "data", "postgres",
             "warehouse", "pipeline", "etl", "bigquery", "snowflake",
             "clickhouse", "duckdb", "redis", "mongodb"],
    "productivity": ["notion", "calendar", "task", "project",
                     "workflow", "collaboration", "kanban", "trello",
                     "asana", "jira", "linear", "todoist"],
    "blockchain": ["solana", "ethereum", "web3", "crypto", "defi",
                   "blockchain", "smart contract", "token", "nft",
                   "wallet", "chain", "onchain"],
    "payments": ["payment", "stripe", "billing", "invoice",
                 "checkout", "subscription", "paypal"],
    "security": ["authentication", "oauth", "encryption", "firewall",
                 "vulnerability", "secret", "credential", "security",
                 "auth", "jwt", "sso"],
    "monitoring": ["monitoring", "logging", "tracing", "alerting",
                   "observability", "metrics", "uptime", "sentry",
                   "datadog", "grafana"],
    "cloud": ["cloud", "serverless", "hosting", "aws", "azure",
              "gcp", "infrastructure", "container", "kubernetes",
              "vercel", "netlify", "render", "railway"],
    "automation": ["automation", "automate", "scheduler", "cron",
                   "workflow", "no-code", "low-code", "zapier",
                   "n8n", "make"],
    "media": ["image", "video", "audio", "streaming", "social media",
              "photo", "podcast", "youtube", "spotify", "instagram"],
    "search": ["search", "indexing", "autocomplete", "elasticsearch",
               "algolia", "meilisearch"],
    "storage": ["storage", "file upload", "cdn", "backup", "s3",
                "bucket", "blob"],
    "cms": ["cms", "content management", "headless", "blog", "wordpress",
            "sanity", "strapi", "contentful"],
    "design": ["design", "figma", "ui", "ux", "wireframe", "prototype",
               "canva", "adobe"],
    "ecommerce": ["ecommerce", "e-commerce", "shop", "cart", "checkout",
                  "inventory", "shipping", "shopify"],
    "documentation": ["documentation", "docs", "api reference", "openapi",
                      "swagger", "readme"],
    "testing": ["test", "jest", "pytest", "cypress", "playwright",
                "selenium", "coverage"],
}


def classify(name: str, desc: str) -> str:
    """Classify a tool into a category by keyword matching."""
    combined = f"{name.lower()} {desc.lower()}"
    hits: dict[str, int] = {}
    for cat, kws in _CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in kws if kw in combined)
        if count > 0:
            hits[cat] = count
    return max(hits, key=hits.get) if hits else "other"


def clean_name(raw_name: str) -> str:
    """Strip HTML artifacts and whitespace from scraped names."""
    cleaned = re.sub(r"<[^>]+>", "", raw_name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 120:
        cleaned = cleaned[:120].rsplit(" ", 1)[0]
    return cleaned


def normalize_queue_entry(entry: dict) -> dict | None:
    """Clean and validate a queue entry before scoring.

    Returns None if the entry is too broken to use.
    """
    name = entry.get("name", "")
    if not name:
        return None

    name = clean_name(name)
    if len(name) < 2:
        return None

    # Skip entries that are clearly HTML garbage
    if name.startswith("<") or "Classification" in name or len(name) > 100 and "\n" in name:
        return None

    entry["name"] = name

    # Clean description
    desc = entry.get("description", "")
    if desc:
        desc = re.sub(r"<[^>]+>", "", desc)
        desc = re.sub(r"\s+", " ", desc).strip()
        if len(desc) > 500:
            desc = desc[:500]
        entry["description"] = desc

    # Normalize type
    source = entry.get("source", "unknown")
    if source == "smithery" and not entry.get("type"):
        entry["type"] = "mcp_server"
    if source in ("pulsemcp", "mcp_so", "mcp_servers_readme", "mcpservers_org", "awesome_mcp_list"):
        entry["type"] = "mcp_server"
    if source == "github_comprehensive" and not entry.get("type"):
        topics = entry.get("topics", [])
        topics_str = " ".join(str(t).lower() for t in topics)
        if any(kw in topics_str for kw in ["mcp", "model-context-protocol", "mcp-server"]):
            entry["type"] = "mcp_server"
        elif any(kw in topics_str for kw in ["skill", "claude-skills", "agent-skill"]):
            entry["type"] = "skill"
        else:
            entry["type"] = "cli_tool"

    if not entry.get("type") or entry["type"] == "?":
        entry["type"] = "general"

    # Map url -> homepage for scorer
    if entry.get("url") and not entry.get("homepage"):
        entry["homepage"] = entry["url"]

    # Map GitHub stars to npm score proxy
    if entry.get("stars"):
        entry["score"] = entry["stars"]

    # Map smithery URL
    if entry.get("smithery_url") and not entry.get("homepage"):
        entry["homepage"] = entry["smithery_url"]

    return entry


def score_and_normalize(entry: dict) -> dict:
    """Score a flat queue entry and produce a service-compatible dict.

    Uses the legacy scorer (tool_scorer.score_tool) which handles flat
    metadata entries correctly, unlike the new type-specific scorer that
    expects nested 'server' dicts for MCP entries.
    """
    source = entry.get("source", "unknown")
    tool_type = entry.get("type", "general")
    name = entry.get("name", "Unknown")
    desc = entry.get("description", "")
    url = entry.get("url", "") or entry.get("homepage", "")
    repo = entry.get("repository", "")
    if isinstance(repo, dict):
        repo = repo.get("url", "")

    # Score using legacy scorer
    scored = legacy_score(entry)

    # Build scan_id
    safe_name = re.sub(r"[^a-z0-9]", "_", name.lower())[:40]
    scan_id = f"tool_{source}_{safe_name}"

    # Map service_type
    type_map = {
        "mcp_server": "mcp_server",
        "skill": "skill",
        "cli_tool": "cli_tool",
        "api": "api",
        "connector": "api",
    }
    service_type = type_map.get(tool_type, "general")

    # Category
    category = entry.get("category", "")
    if not category or category in ("mcp_server", "skill", "other", ""):
        category = classify(name, desc)

    # Cross-references
    cross_refs: dict[str, str] = {}
    if entry.get("npm_url"):
        cross_refs["npm"] = entry["npm_url"]
    if repo and "github.com" in str(repo):
        cross_refs["github"] = str(repo)
    if entry.get("pypi_url"):
        cross_refs["pypi"] = entry["pypi_url"]
    if entry.get("smithery_url"):
        cross_refs["smithery"] = entry["smithery_url"]

    # Tags
    tags = entry.get("keywords", []) or entry.get("topics", [])
    if isinstance(tags, list):
        tags = [str(t) for t in tags[:5]]
    else:
        tags = []

    # Auto-extract keywords from description when no tags
    if not tags and desc:
        stop = {"this", "that", "with", "from", "your", "have", "will", "been",
                "they", "them", "their", "what", "when", "which", "there", "about",
                "into", "than", "also", "more", "some", "very", "just", "other",
                "over", "such", "only", "does", "most", "like", "make", "made",
                "each", "well", "were", "then", "used", "many", "using", "tool",
                "tools", "allows", "provides", "support", "based", "helps", "enable"}
        words = re.findall(r"[a-zA-Z]{4,}", desc.lower())
        filtered = [w for w in words if w not in stop]
        from collections import Counter as C
        tags = [w for w, _ in C(filtered).most_common(5)]

    return {
        "scan_id": scan_id,
        "url": url,
        "service_name": name,
        "description": desc,
        "clarvia_score": scored["clarvia_score"],
        "rating": scored["rating"],
        "dimensions": scored["dimensions"],
        "category": category,
        "service_type": service_type,
        "type_config": None,
        "scanned_at": entry.get("discovered_at"),
        "source": f"collected:{source}",
        "tags": tags,
        "pricing": detect_pricing(entry),
        "capabilities": extract_capabilities(entry),
        "difficulty": detect_difficulty(entry),
        "popularity": estimate_popularity(entry),
        "cross_refs": cross_refs,
    }


def deduplicate(scored_tools: list[dict]) -> list[dict]:
    """Deduplicate by normalized name, keeping highest score."""
    by_name: dict[str, dict] = {}

    for tool in scored_tools:
        name = tool.get("service_name", "").lower().strip()
        name_key = re.sub(r"[^a-z0-9]", "", name)
        if not name_key:
            continue

        if name_key in by_name:
            if tool.get("clarvia_score", 0) > by_name[name_key].get("clarvia_score", 0):
                by_name[name_key] = tool
        else:
            by_name[name_key] = tool

    return list(by_name.values())


def write_to_sqlite(tools: list[dict], db_path: Path) -> int:
    """Write scored tools to SQLite for persistence."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            scan_id         TEXT PRIMARY KEY,
            url             TEXT NOT NULL DEFAULT '',
            service_name    TEXT NOT NULL,
            description     TEXT DEFAULT '',
            clarvia_score   INTEGER NOT NULL DEFAULT 0,
            rating          TEXT NOT NULL DEFAULT 'Low',
            dimensions      TEXT DEFAULT '{}',
            category        TEXT DEFAULT 'other',
            service_type    TEXT DEFAULT 'general',
            type_config     TEXT,
            source          TEXT DEFAULT '',
            tags            TEXT DEFAULT '[]',
            pricing         TEXT DEFAULT 'unknown',
            capabilities    TEXT DEFAULT '[]',
            difficulty      TEXT DEFAULT 'medium',
            popularity      INTEGER DEFAULT 0,
            cross_refs      TEXT DEFAULT '{}',
            scanned_at      TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    inserted = 0
    for tool in tools:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO services
                (scan_id, url, service_name, description, clarvia_score, rating,
                 dimensions, category, service_type, type_config, source, tags,
                 pricing, capabilities, difficulty, popularity, cross_refs, scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tool.get("scan_id", ""),
                tool.get("url", ""),
                tool.get("service_name", ""),
                tool.get("description", ""),
                tool.get("clarvia_score", 0),
                tool.get("rating", "Low"),
                json.dumps(tool.get("dimensions", {})),
                tool.get("category", "other"),
                tool.get("service_type", "general"),
                json.dumps(tool.get("type_config")) if tool.get("type_config") else None,
                tool.get("source", ""),
                json.dumps(tool.get("tags", [])),
                tool.get("pricing", "unknown"),
                json.dumps(tool.get("capabilities", [])),
                tool.get("difficulty", "medium"),
                tool.get("popularity", 0),
                json.dumps(tool.get("cross_refs", {})),
                tool.get("scanned_at"),
            ))
            inserted += 1
        except Exception as e:
            log.warning("DB insert failed for %s: %s", tool.get("scan_id", "?"), e)

    conn.commit()
    conn.close()
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Batch metadata scoring pipeline")
    parser.add_argument("--limit", type=int, default=0, help="Max tools to process (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Score but don't write output")
    parser.add_argument("--min-score", type=int, default=10, help="Minimum score to include (default: 10)")
    parser.add_argument("--no-db", action="store_true", help="Skip SQLite write")
    parser.add_argument("--keep-existing", action="store_true", help="Keep existing prebuilt-scans.json entries")
    args = parser.parse_args()

    if not QUEUE_FILE.exists():
        log.error("Queue file not found: %s", QUEUE_FILE)
        sys.exit(1)

    # Load existing prebuilt-scans if keeping
    existing_tools: list[dict] = []
    if args.keep_existing and OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing_tools = json.load(f)
        log.info("Loaded %d existing prebuilt scans", len(existing_tools))

    # Count lines first
    total_lines = sum(1 for _ in open(QUEUE_FILE))
    limit = args.limit if args.limit > 0 else total_lines
    log.info("Queue: %d tools, processing: %d, min_score: %d", total_lines, limit, args.min_score)

    # Process
    scored_tools: list[dict] = list(existing_tools)
    errors = 0
    skipped_bad = 0
    skipped_low = 0
    scores: list[int] = []
    source_counts: Counter = Counter()
    t0 = time.time()

    with open(QUEUE_FILE) as f:
        for i, line in enumerate(f):
            if i >= limit:
                break

            try:
                raw = json.loads(line.strip())
            except json.JSONDecodeError:
                errors += 1
                continue

            # Clean and normalize
            cleaned = normalize_queue_entry(raw)
            if cleaned is None:
                skipped_bad += 1
                continue

            # Score
            try:
                normalized = score_and_normalize(cleaned)
            except Exception as e:
                errors += 1
                if errors <= 10:
                    log.warning("Scoring failed for '%s': %s", cleaned.get("name", "?"), e)
                continue

            score = normalized.get("clarvia_score", 0)
            scores.append(score)
            source_counts[cleaned.get("source", "unknown")] += 1

            if score < args.min_score:
                skipped_low += 1
                continue

            scored_tools.append(normalized)

            # Progress log
            processed = i + 1
            if processed % 2000 == 0:
                elapsed = time.time() - t0
                rate = processed / elapsed if elapsed > 0 else 0
                log.info(
                    "Progress: %d/%d (%.0f/s) | kept: %d | errors: %d | low: %d | bad: %d",
                    processed, limit, rate, len(scored_tools) - len(existing_tools),
                    errors, skipped_low, skipped_bad,
                )

    elapsed = time.time() - t0

    # Deduplicate
    before_dedup = len(scored_tools)
    scored_tools = deduplicate(scored_tools)
    after_dedup = len(scored_tools)

    # Sort by score descending
    scored_tools.sort(key=lambda x: x.get("clarvia_score", 0), reverse=True)

    # Stats
    log.info("=" * 60)
    log.info("BATCH SCORING COMPLETE")
    log.info("=" * 60)
    log.info("Time: %.1fs (%.0f tools/sec)", elapsed, (limit / elapsed) if elapsed > 0 else 0)
    log.info("Processed: %d | Errors: %d | Bad entries: %d", len(scores), errors, skipped_bad)
    log.info("Skipped (score < %d): %d", args.min_score, skipped_low)
    log.info("Before dedup: %d | After dedup: %d | Removed: %d",
             before_dedup, after_dedup, before_dedup - after_dedup)

    if scores:
        log.info("Score distribution:")
        log.info("  Min: %d | Max: %d | Avg: %.1f | Median: %d | Stddev: %.1f",
                 min(scores), max(scores), statistics.mean(scores),
                 int(statistics.median(scores)),
                 statistics.stdev(scores) if len(scores) > 1 else 0)

        buckets = {"0-19": 0, "20-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
        for s in scores:
            if s < 20:
                buckets["0-19"] += 1
            elif s < 40:
                buckets["20-39"] += 1
            elif s < 60:
                buckets["40-59"] += 1
            elif s < 80:
                buckets["60-79"] += 1
            else:
                buckets["80-100"] += 1
        log.info("  Buckets: %s", " | ".join(f"{k}: {v}" for k, v in buckets.items()))

        log.info("By source: %s", " | ".join(f"{k}: {v}" for k, v in source_counts.most_common()))

        ratings = Counter(t.get("rating", "?") for t in scored_tools)
        log.info("Ratings: %s", " | ".join(f"{k}: {v}" for k, v in ratings.most_common()))

    if args.dry_run:
        log.info("DRY RUN — no files written")
        return

    # Write to prebuilt-scans.json
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(scored_tools, f, separators=(",", ":"), ensure_ascii=False)
    file_mb = OUTPUT_FILE.stat().st_size / 1024 / 1024
    log.info("Wrote %d tools to %s (%.1f MB)", len(scored_tools), OUTPUT_FILE, file_mb)

    # Write to SQLite
    if not args.no_db:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        db_count = write_to_sqlite(scored_tools, DB_FILE)
        log.info("Wrote %d tools to SQLite: %s", db_count, DB_FILE)

    log.info("Done. Restart the API server to pick up new data.")


if __name__ == "__main__":
    main()
