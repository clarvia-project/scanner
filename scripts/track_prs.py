#!/usr/bin/env python3
"""Track Clarvia-related GitHub PRs (awesome-list submissions, badge PRs, etc.).

Uses the `gh` CLI (GitHub CLI) to search for PRs authored by the Clarvia
GitHub account and logs their status to data/pr-tracking.jsonl.

Usage:
  python scripts/track_prs.py                    # full scan
  python scripts/track_prs.py --author digitamaz  # custom author
  python scripts/track_prs.py --repos awesome-mcp-servers,awesome-ai-tools

Features:
  - Searches PRs by author across GitHub
  - Tracks specific repos if provided
  - Appends new status entries to JSONL (append-only log)
  - Detects state changes (open -> merged, etc.) and logs transitions
  - Can be called by a scheduled task for continuous monitoring
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_AUTHOR = "digitamaz"

# Repos we specifically care about (awesome lists, directories, etc.)
TRACKED_REPOS = [
    "wong2/awesome-mcp-servers",
    "modelcontextprotocol/servers",
    "cursor/awesome-cursor-rules",
    "agentic-labs/awesome-ai-agents",
    "f/awesome-chatgpt-prompts",
    "sindresorhus/awesome",
]

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "pr-tracking.jsonl"


def run_gh(args: list[str], timeout: int = 30) -> str | None:
    """Execute a gh CLI command and return stdout, or None on failure."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "no pull requests match" in stderr.lower() or "no results" in stderr.lower():
                return "[]"
            logger.warning("gh command failed: %s\nstderr: %s", " ".join(cmd), stderr)
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        logger.error("gh CLI not found. Install: https://cli.github.com/")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        logger.warning("gh command timed out: %s", " ".join(cmd))
        return None


def search_prs_by_author(author: str) -> list[dict]:
    """Search all PRs authored by the given user across GitHub.

    Uses two strategies:
    1. gh search prs --author (works for most public users)
    2. If that fails, uses gh api with authenticated search (works for own PRs)
    """
    logger.info("Searching PRs by author: %s", author)

    # Strategy 1: gh search prs
    output = run_gh([
        "search", "prs",
        "--author", author,
        "--json", "number,title,state,url,repository,createdAt,updatedAt,closedAt",
        "--limit", "100",
    ], timeout=60)

    if output:
        try:
            prs = json.loads(output)
            if isinstance(prs, list) and prs:
                return prs
        except json.JSONDecodeError:
            pass

    # Strategy 2: gh api (uses authenticated token, more reliable for own PRs)
    logger.info("Falling back to gh api search for author: %s", author)
    output = run_gh([
        "api", "search/issues",
        "-X", "GET",
        "-f", f"q=author:{author} type:pr",
        "-f", "per_page=100",
        "--jq", ".items",
    ], timeout=60)

    if output:
        try:
            items = json.loads(output)
            if isinstance(items, list):
                # Normalize GitHub API format to match gh search format
                return [
                    {
                        "number": item.get("number", 0),
                        "title": item.get("title", ""),
                        "state": "MERGED" if item.get("pull_request", {}).get("merged_at") else item.get("state", "").upper(),
                        "url": item.get("pull_request", {}).get("html_url", item.get("html_url", "")),
                        "repository": {"nameWithOwner": "/".join(item.get("repository_url", "").split("/")[-2:])},
                        "createdAt": item.get("created_at", ""),
                        "updatedAt": item.get("updated_at", ""),
                        "closedAt": item.get("closed_at"),
                    }
                    for item in items
                    if item.get("pull_request")  # only actual PRs
                ]
        except json.JSONDecodeError:
            pass

    return []


def check_repo_prs(repo: str, author: str) -> list[dict]:
    """Check PRs in a specific repo by the given author.

    Uses gh pr list for the specific repo, which is more reliable
    than search when the user's profile is not publicly searchable.
    """
    logger.info("Checking repo: %s", repo)

    # Use gh pr list which works even when search doesn't
    output = run_gh([
        "pr", "list",
        "--repo", repo,
        "--author", author,
        "--state", "all",
        "--json", "number,title,state,url,createdAt,updatedAt,closedAt,mergedAt",
        "--limit", "50",
    ], timeout=30)

    if output is None:
        return []

    try:
        prs = json.loads(output)
        if isinstance(prs, list):
            # Normalize to our format
            for pr in prs:
                pr["repository"] = {"nameWithOwner": repo}
            return prs
        return []
    except json.JSONDecodeError:
        return []


def load_existing_tracking(path: Path) -> dict[str, dict]:
    """Load existing tracking data, keyed by PR URL.

    Returns the latest entry for each URL.
    """
    latest: dict[str, dict] = {}

    if not path.exists():
        return latest

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                url = entry.get("url", "")
                if url:
                    latest[url] = entry
            except json.JSONDecodeError:
                continue

    return latest


def check_if_merged(pr_url: str) -> bool:
    """Use gh pr view to check if a closed PR was actually merged."""
    if not pr_url:
        return False
    # Extract owner/repo and number from URL
    # URL format: https://github.com/owner/repo/pull/123
    try:
        parts = pr_url.rstrip("/").split("/")
        owner_repo = f"{parts[-4]}/{parts[-3]}"
        number = parts[-1]
        output = run_gh([
            "pr", "view", number,
            "--repo", owner_repo,
            "--json", "mergedAt,state",
        ], timeout=15)
        if output:
            data = json.loads(output)
            return bool(data.get("mergedAt"))
    except (IndexError, json.JSONDecodeError, Exception):
        pass
    return False


def normalize_pr(pr: dict) -> dict:
    """Normalize a PR from gh CLI output to our tracking format."""
    repo_info = pr.get("repository", {})
    repo_name = repo_info.get("nameWithOwner", "") if isinstance(repo_info, dict) else str(repo_info)

    # Determine effective state
    # gh pr list returns OPEN/CLOSED/MERGED; gh search may only return OPEN/CLOSED
    state = pr.get("state", "UNKNOWN").upper()
    merged_at = pr.get("mergedAt")

    if state == "MERGED" or merged_at:
        effective_state = "merged"
    elif state == "CLOSED":
        # For search results without mergedAt, check via API
        url = pr.get("url", "")
        if url and check_if_merged(url):
            effective_state = "merged"
        else:
            effective_state = "closed"
    elif state == "OPEN":
        effective_state = "open"
    else:
        effective_state = state.lower()

    return {
        "url": pr.get("url", ""),
        "repo": repo_name,
        "number": pr.get("number", 0),
        "title": pr.get("title", ""),
        "state": effective_state,
        "created_at": pr.get("createdAt", ""),
        "updated_at": pr.get("updatedAt", ""),
        "merged_at": merged_at or None,
        "closed_at": pr.get("closedAt") or None,
    }


def track_prs(
    author: str,
    repos: list[str],
    output_path: Path,
) -> list[dict]:
    """Main tracking logic. Returns list of all tracked PRs with their status."""

    # 1. Search globally by author
    all_prs = search_prs_by_author(author)

    # 2. Also check specific repos (may overlap, we deduplicate)
    seen_urls: set[str] = {pr.get("url", "") for pr in all_prs}

    for repo in repos:
        repo_prs = check_repo_prs(repo, author)
        for pr in repo_prs:
            url = pr.get("url", "")
            if url and url not in seen_urls:
                all_prs.append(pr)
                seen_urls.add(url)

    if not all_prs:
        logger.info("No PRs found for author: %s", author)
        return []

    # 3. Normalize
    normalized = [normalize_pr(pr) for pr in all_prs]
    logger.info("Found %d PRs total", len(normalized))

    # 4. Load existing tracking to detect state changes
    existing = load_existing_tracking(output_path)

    # 5. Write new entries (append-only)
    now = datetime.now(timezone.utc).isoformat()
    new_entries: list[dict] = []

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "a") as f:
        for pr in normalized:
            url = pr["url"]
            prev = existing.get(url)

            # Detect state change
            prev_state = prev["state"] if prev else None
            state_changed = prev_state is not None and prev_state != pr["state"]

            entry = {
                **pr,
                "tracked_at": now,
                "state_changed": state_changed,
                "previous_state": prev_state if state_changed else None,
            }

            # Always log if state changed or if this is a new PR
            if state_changed or prev is None:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                new_entries.append(entry)

                if state_changed:
                    logger.info(
                        "State change: %s -> %s for %s",
                        prev_state, pr["state"], pr["title"],
                    )
                else:
                    logger.info("New PR tracked: [%s] %s", pr["state"], pr["title"])

    if not new_entries:
        # Still write a heartbeat entry so we know the script ran
        heartbeat = {
            "type": "heartbeat",
            "tracked_at": now,
            "total_prs": len(normalized),
            "states": {},
        }
        state_counts: dict[str, int] = {}
        for pr in normalized:
            state_counts[pr["state"]] = state_counts.get(pr["state"], 0) + 1
        heartbeat["states"] = state_counts

        with open(output_path, "a") as f:
            f.write(json.dumps(heartbeat, ensure_ascii=False) + "\n")

        logger.info("No state changes detected. Heartbeat logged.")

    return normalized


def main():
    parser = argparse.ArgumentParser(
        description="Track Clarvia-related GitHub PRs",
    )
    parser.add_argument(
        "--author",
        type=str,
        default=DEFAULT_AUTHOR,
        help=f"GitHub username to search PRs for (default: {DEFAULT_AUTHOR})",
    )
    parser.add_argument(
        "--repos",
        type=str,
        default=None,
        help="Comma-separated list of repos to check (default: built-in list)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSONL path (default: data/pr-tracking.jsonl)",
    )
    args = parser.parse_args()

    repos = args.repos.split(",") if args.repos else TRACKED_REPOS
    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT

    prs = track_prs(args.author, repos, output_path)

    if not prs:
        print("\nNo PRs found.")
        return

    # Console summary
    state_counts: dict[str, int] = {}
    for pr in prs:
        state_counts[pr["state"]] = state_counts.get(pr["state"], 0) + 1

    print("\n" + "=" * 72)
    print(f" PR Tracking Summary ({args.author})")
    print("=" * 72)
    print(f" Total: {len(prs)}")
    for state, count in sorted(state_counts.items()):
        icon = {"open": "O", "merged": "M", "closed": "X"}.get(state, "?")
        print(f"   [{icon}] {state}: {count}")
    print("-" * 72)

    for pr in prs:
        state_icon = {"open": "O", "merged": "M", "closed": "X"}.get(pr["state"], "?")
        print(f"  [{state_icon}] {pr['repo']}#{pr['number']}: {pr['title']}")
        print(f"      {pr['url']}")

    print("-" * 72)
    print(f" Log: {output_path}")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
