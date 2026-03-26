#!/usr/bin/env python3
"""Clarvia Data Quality Auto-Auditor.

Automatically detects and fixes data quality degradation across the
Clarvia tool catalog.

Checks:
  1. Score distribution  — Alert if new tools deviate >2 std from historical mean
  2. Category distribution — Alert if "other" category exceeds 40%
  3. Duplicate detection  — Flag tools with >90% name/URL similarity
  4. Freshness check      — Alert if no new tools added in 7 days
  5. Completeness check   — Flag tools missing description, score, or category
  6. Anomaly detection    — Quarantine if single harvester run adds >500 tools

Auto-fixes:
  - Remove exact duplicate entries
  - Re-classify "other" category tools (flag for classifier re-run)

Usage:
    python scripts/automation/data_auditor.py
    python scripts/automation/data_auditor.py --dry-run
    python scripts/automation/data_auditor.py --fix   # Apply auto-fixes
"""

import argparse
import json
import logging
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
AUDIT_DIR = DATA_DIR / "audits"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"
QUEUE_PATH = DATA_DIR / "new-tools-queue.jsonl"
DISCOVERIES_PATH = DATA_DIR / "harvester" / "discoveries.jsonl"

sys.path.insert(0, str(SCRIPT_DIR.parent))
from telegram_notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

SCORE_STD_THRESHOLD = 2.0          # Alert if new tools deviate > 2 std
OTHER_CATEGORY_THRESHOLD = 0.40    # 40% "other" is suspicious
SIMILARITY_THRESHOLD = 0.90        # 90% name/URL similarity = likely dupe
FRESHNESS_DAYS = 7                 # No new tools in 7 days = stale
ANOMALY_BATCH_SIZE = 500           # Single run adding 500+ tools = bug


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_catalog() -> list[dict]:
    """Load the prebuilt scans catalog."""
    if not PREBUILT_PATH.exists():
        logger.warning("No prebuilt scans file found at %s", PREBUILT_PATH)
        return []
    try:
        with open(PREBUILT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse prebuilt scans: %s", exc)
        return []


def load_discoveries(days: int = 30) -> list[dict]:
    """Load recent discoveries from JSONL file."""
    if not DISCOVERIES_PATH.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = []

    try:
        with open(DISCOVERIES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    discovered = entry.get("discovered_at", "")
                    if discovered:
                        if discovered.endswith("Z"):
                            discovered = discovered.replace("Z", "+00:00")
                        try:
                            dt = datetime.fromisoformat(discovered)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            if dt >= cutoff:
                                entries.append(entry)
                        except (ValueError, TypeError):
                            entries.append(entry)
                    else:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except IOError as exc:
        logger.error("Failed to read discoveries: %s", exc)

    return entries


def load_queue() -> list[dict]:
    """Load the pending scan queue."""
    if not QUEUE_PATH.exists():
        return []

    entries = []
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except IOError:
        pass
    return entries


# ---------------------------------------------------------------------------
# Audit checks
# ---------------------------------------------------------------------------

def check_score_distribution(catalog: list[dict]) -> dict:
    """Check if score distribution of recent tools is anomalous."""
    result = {"check": "score_distribution", "status": "ok", "issues": []}

    all_scores = [
        t.get("score", 0) for t in catalog
        if isinstance(t.get("score"), (int, float)) and t.get("score", 0) > 0
    ]

    if len(all_scores) < 10:
        result["status"] = "skipped"
        result["reason"] = f"Too few scored tools ({len(all_scores)})"
        return result

    mean = sum(all_scores) / len(all_scores)
    variance = sum((s - mean) ** 2 for s in all_scores) / len(all_scores)
    std = math.sqrt(variance) if variance > 0 else 1.0

    # Check recent additions (last 7 days based on scanned_at or created)
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_scores = []
    for t in catalog:
        scanned = t.get("scanned_at") or t.get("created_at") or ""
        if scanned:
            try:
                if scanned.endswith("Z"):
                    scanned = scanned.replace("Z", "+00:00")
                dt = datetime.fromisoformat(scanned)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    score = t.get("score", 0)
                    if isinstance(score, (int, float)):
                        recent_scores.append(score)
            except (ValueError, TypeError):
                continue

    result["historical_mean"] = round(mean, 2)
    result["historical_std"] = round(std, 2)
    result["recent_count"] = len(recent_scores)

    if len(recent_scores) < 3:
        result["reason"] = "Not enough recent scores to evaluate"
        return result

    recent_mean = sum(recent_scores) / len(recent_scores)
    result["recent_mean"] = round(recent_mean, 2)

    deviation = abs(recent_mean - mean) / std if std > 0 else 0
    result["deviation_std"] = round(deviation, 2)

    if deviation > SCORE_STD_THRESHOLD:
        result["status"] = "alert"
        result["issues"].append(
            f"Recent score mean ({recent_mean:.1f}) deviates {deviation:.1f} std "
            f"from historical mean ({mean:.1f} +/- {std:.1f})"
        )

    return result


def check_category_distribution(catalog: list[dict]) -> dict:
    """Check if 'other' category is overrepresented."""
    result = {"check": "category_distribution", "status": "ok", "issues": []}

    categories = [t.get("category", "other").lower() for t in catalog]
    if not categories:
        result["status"] = "skipped"
        return result

    counter = Counter(categories)
    total = len(categories)
    other_count = counter.get("other", 0) + counter.get("uncategorized", 0)
    other_pct = other_count / total if total > 0 else 0

    result["total_tools"] = total
    result["other_count"] = other_count
    result["other_pct"] = round(other_pct * 100, 1)
    result["top_categories"] = dict(counter.most_common(10))

    if other_pct > OTHER_CATEGORY_THRESHOLD:
        result["status"] = "alert"
        result["issues"].append(
            f"'Other' category at {other_pct*100:.1f}% ({other_count}/{total}) "
            f"exceeds {OTHER_CATEGORY_THRESHOLD*100:.0f}% threshold — "
            f"classifier may be degraded"
        )

    return result


def check_duplicates(catalog: list[dict]) -> dict:
    """Find tools with >90% name/URL similarity."""
    result = {"check": "duplicates", "status": "ok", "issues": [], "duplicates": []}

    if len(catalog) < 2:
        result["status"] = "skipped"
        return result

    # Build comparison lists
    tools = []
    for t in catalog:
        name = (t.get("name") or "").lower().strip()
        url = (t.get("url") or "").lower().strip().rstrip("/")
        if name or url:
            tools.append({"name": name, "url": url, "original": t})

    # Exact URL duplicates first (fast)
    url_groups: dict[str, list[int]] = {}
    for i, t in enumerate(tools):
        if t["url"]:
            url_groups.setdefault(t["url"], []).append(i)

    exact_dupes = []
    for url, indices in url_groups.items():
        if len(indices) > 1:
            exact_dupes.append({
                "type": "exact_url",
                "url": url,
                "count": len(indices),
                "names": [tools[i]["name"] for i in indices],
            })

    result["exact_url_duplicates"] = len(exact_dupes)
    if exact_dupes:
        result["duplicates"].extend(exact_dupes[:20])

    # Fuzzy name similarity (sample to avoid O(n^2) explosion)
    sample_size = min(len(tools), 500)
    sample = tools[:sample_size]

    fuzzy_dupes = []
    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            name_sim = SequenceMatcher(
                None, sample[i]["name"], sample[j]["name"]
            ).ratio()
            if name_sim >= SIMILARITY_THRESHOLD and sample[i]["name"]:
                fuzzy_dupes.append({
                    "type": "fuzzy_name",
                    "name_a": sample[i]["name"],
                    "name_b": sample[j]["name"],
                    "similarity": round(name_sim, 3),
                    "url_a": sample[i]["url"],
                    "url_b": sample[j]["url"],
                })

    result["fuzzy_name_duplicates"] = len(fuzzy_dupes)
    if fuzzy_dupes:
        result["duplicates"].extend(fuzzy_dupes[:20])

    total_dupes = len(exact_dupes) + len(fuzzy_dupes)
    if total_dupes > 0:
        result["status"] = "alert" if total_dupes > 5 else "warning"
        result["issues"].append(
            f"Found {len(exact_dupes)} exact URL dupes + {len(fuzzy_dupes)} fuzzy name dupes"
        )

    return result


def check_freshness(catalog: list[dict]) -> dict:
    """Check if new tools have been added recently."""
    result = {"check": "freshness", "status": "ok", "issues": []}

    cutoff = datetime.now(timezone.utc) - timedelta(days=FRESHNESS_DAYS)
    recent = 0

    latest_date = None
    for t in catalog:
        scanned = t.get("scanned_at") or t.get("created_at") or ""
        if scanned:
            try:
                if scanned.endswith("Z"):
                    scanned = scanned.replace("Z", "+00:00")
                dt = datetime.fromisoformat(scanned)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    recent += 1
                if latest_date is None or dt > latest_date:
                    latest_date = dt
            except (ValueError, TypeError):
                continue

    result["recent_additions"] = recent
    result["freshness_days"] = FRESHNESS_DAYS
    if latest_date:
        result["latest_addition"] = latest_date.isoformat()
        days_since = (datetime.now(timezone.utc) - latest_date).days
        result["days_since_latest"] = days_since

    if recent == 0:
        result["status"] = "alert"
        result["issues"].append(
            f"No new tools added in the last {FRESHNESS_DAYS} days — "
            f"harvester may be broken"
        )

    return result


def check_completeness(catalog: list[dict]) -> dict:
    """Find tools missing essential fields."""
    result = {"check": "completeness", "status": "ok", "issues": [], "incomplete_tools": []}

    required_fields = ["description", "category", "url"]
    score_field = "score"

    missing_desc = 0
    missing_category = 0
    missing_score = 0
    missing_url = 0

    for t in catalog:
        missing = []
        name = t.get("name") or t.get("url", "unknown")

        if not t.get("description"):
            missing_desc += 1
            missing.append("description")
        if not t.get("category"):
            missing_category += 1
            missing.append("category")
        if not isinstance(t.get(score_field), (int, float)):
            missing_score += 1
            missing.append("score")
        if not t.get("url"):
            missing_url += 1
            missing.append("url")

        if missing:
            result["incomplete_tools"].append({
                "name": name[:60],
                "missing": missing,
            })

    total = len(catalog)
    result["total_tools"] = total
    result["missing_description"] = missing_desc
    result["missing_category"] = missing_category
    result["missing_score"] = missing_score
    result["missing_url"] = missing_url

    # Trim incomplete list for readability
    result["incomplete_tools"] = result["incomplete_tools"][:50]

    incomplete_pct = len(result["incomplete_tools"]) / total if total > 0 else 0
    if incomplete_pct > 0.2:
        result["status"] = "alert"
        result["issues"].append(
            f"{len(result['incomplete_tools'])} tools ({incomplete_pct*100:.0f}%) "
            f"are missing essential fields"
        )
    elif result["incomplete_tools"]:
        result["status"] = "warning"
        result["issues"].append(
            f"{len(result['incomplete_tools'])} tools have incomplete data"
        )

    return result


def check_anomaly_batch(discoveries: list[dict]) -> dict:
    """Detect suspiciously large batches from a single harvester run."""
    result = {"check": "anomaly_batch", "status": "ok", "issues": []}

    if not discoveries:
        result["status"] = "skipped"
        return result

    # Group by discovered_at date (to approximate "run")
    by_date: dict[str, list[dict]] = {}
    for d in discoveries:
        dt_str = d.get("discovered_at", "")[:10]  # YYYY-MM-DD
        if dt_str:
            by_date.setdefault(dt_str, []).append(d)

    result["days_checked"] = len(by_date)
    anomalous_batches = []

    for date, batch in by_date.items():
        # Also check per-source within a day
        by_source: dict[str, int] = {}
        for d in batch:
            src = d.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1

        for source, count in by_source.items():
            if count > ANOMALY_BATCH_SIZE:
                anomalous_batches.append({
                    "date": date,
                    "source": source,
                    "count": count,
                })

    result["anomalous_batches"] = anomalous_batches
    if anomalous_batches:
        result["status"] = "alert"
        for ab in anomalous_batches:
            result["issues"].append(
                f"Anomalous batch on {ab['date']}: {ab['source']} added "
                f"{ab['count']} tools (> {ANOMALY_BATCH_SIZE} threshold)"
            )

    return result


# ---------------------------------------------------------------------------
# Auto-fix routines
# ---------------------------------------------------------------------------

def fix_exact_duplicates(catalog: list[dict]) -> tuple[list[dict], int]:
    """Remove exact URL duplicates, keeping the one with the highest score."""
    seen_urls: dict[str, int] = {}  # url -> index of best entry
    to_keep = []
    removed = 0

    for i, tool in enumerate(catalog):
        url = (tool.get("url") or "").strip().rstrip("/").lower()
        if not url:
            to_keep.append(tool)
            continue

        if url in seen_urls:
            # Keep the one with the higher score
            existing_idx = seen_urls[url]
            existing_score = to_keep[existing_idx].get("score", 0) or 0
            new_score = tool.get("score", 0) or 0
            if new_score > existing_score:
                to_keep[existing_idx] = tool
            removed += 1
        else:
            seen_urls[url] = len(to_keep)
            to_keep.append(tool)

    return to_keep, removed


def flag_for_reclassification(catalog: list[dict]) -> int:
    """Flag 'other' category tools for re-classification."""
    flagged = 0
    for tool in catalog:
        cat = (tool.get("category") or "").lower()
        if cat in ("other", "uncategorized", ""):
            tool["_needs_reclassification"] = True
            flagged += 1
    return flagged


# ---------------------------------------------------------------------------
# Main audit pipeline
# ---------------------------------------------------------------------------

def run_audit(*, dry_run: bool = False, apply_fixes: bool = False) -> dict:
    """Run the full data quality audit.

    Returns:
        Audit report dict.
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "summary": {"ok": 0, "warning": 0, "alert": 0, "skipped": 0},
        "fixes_applied": [],
    }

    catalog = load_catalog()
    discoveries = load_discoveries(days=30)

    logger.info("Loaded %d catalog entries, %d recent discoveries", len(catalog), len(discoveries))

    # Run checks
    checks = [
        check_score_distribution(catalog),
        check_category_distribution(catalog),
        check_duplicates(catalog),
        check_freshness(catalog),
        check_completeness(catalog),
        check_anomaly_batch(discoveries),
    ]

    for check in checks:
        status = check.get("status", "ok")
        report["summary"][status] = report["summary"].get(status, 0) + 1
        report["checks"].append(check)

    # Collect all issues for alerting
    all_issues = []
    for check in checks:
        for issue in check.get("issues", []):
            all_issues.append(f"[{check['check']}] {issue}")

    report["total_issues"] = len(all_issues)

    # Apply fixes if requested
    if apply_fixes and not dry_run:
        # Fix 1: Remove exact duplicates
        cleaned, dupe_count = fix_exact_duplicates(catalog)
        if dupe_count > 0:
            # Write back cleaned catalog
            with open(PREBUILT_PATH, "w", encoding="utf-8") as f:
                json.dump(cleaned, f, indent=2, default=str)
            report["fixes_applied"].append(
                f"Removed {dupe_count} exact URL duplicates"
            )
            logger.info("Removed %d exact URL duplicates", dupe_count)

        # Fix 2: Flag for reclassification
        flagged = flag_for_reclassification(cleaned)
        if flagged > 0:
            report["fixes_applied"].append(
                f"Flagged {flagged} 'other' category tools for reclassification"
            )
            logger.info("Flagged %d tools for reclassification", flagged)

    # Send alerts for significant issues
    alert_issues = [
        issue for check in checks
        if check.get("status") == "alert"
        for issue in check.get("issues", [])
    ]

    if alert_issues and not dry_run:
        body = "\n".join(f"• {issue}" for issue in alert_issues[:10])
        if len(alert_issues) > 10:
            body += f"\n... and {len(alert_issues) - 10} more issues"

        send_alert(
            "Data Quality Audit: Issues Detected",
            f"Found {len(alert_issues)} data quality issues:\n\n{body}",
            level="WARNING",
        )

    # Save audit report
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = AUDIT_DIR / f"audit-{today}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(
        "Audit complete: %d checks, %d issues found, %d fixes applied",
        len(checks), len(all_issues), len(report["fixes_applied"]),
    )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Clarvia Data Quality Auditor")
    parser.add_argument("--dry-run", action="store_true", help="Don't send alerts or apply fixes")
    parser.add_argument("--fix", action="store_true", help="Apply auto-fixes (dedup, re-flag)")
    args = parser.parse_args()

    report = run_audit(dry_run=args.dry_run, apply_fixes=args.fix or not args.dry_run)
    print(json.dumps(report, indent=2, default=str))

    # Exit with error code if alerts were raised
    has_alerts = report["summary"].get("alert", 0) > 0
    sys.exit(1 if has_alerts else 0)


if __name__ == "__main__":
    main()
