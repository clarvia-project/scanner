#!/usr/bin/env python3
"""Auto Badge PR Submission — Creates PRs to add Clarvia badges to tool READMEs.

Reads badge-outreach.json for eligible tools, forks their repos, adds a badge
section to README.md, and creates a PR. Tracks submissions in data/badge-prs.jsonl
to avoid duplicates.

Usage:
  python scripts/auto_badge_pr.py                    # default: max 3 PRs
  python scripts/auto_badge_pr.py --limit 5          # up to 5 PRs
  python scripts/auto_badge_pr.py --dry-run           # preview only
  python scripts/auto_badge_pr.py --min-score 80      # higher threshold

Features:
  - Idempotent: skips repos with existing PR entries in badge-prs.jsonl
  - Rate-limited: max N PRs per run (default 3) to avoid spam
  - Uses gh CLI for all GitHub operations (fork, branch, commit, PR)
  - Logs all attempts (success and failure) to badge-prs.jsonl
"""

import argparse
import json
import logging
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BADGE_OUTREACH_PATH = PROJECT_ROOT / "data" / "badge-outreach.json"
BADGE_PRS_PATH = PROJECT_ROOT / "data" / "badge-prs.jsonl"
GITHUB_AUTHOR = "digitamaz"
BRANCH_NAME = "add-clarvia-badge"
PR_DELAY_SECONDS = 5  # delay between PRs to be polite


def run_gh(args: list[str], timeout: int = 60) -> Optional[str]:
    """Execute a gh CLI command and return stdout, or None on failure."""
    cmd = ["gh"] + args
    logger.debug("Running: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            logger.warning("gh command failed: %s\nstderr: %s", " ".join(cmd), result.stderr.strip())
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("gh command timed out: %s", " ".join(cmd))
        return None
    except FileNotFoundError:
        logger.error("gh CLI not found. Install: https://cli.github.com/")
        return None


def load_badge_outreach() -> list[dict]:
    """Load tools eligible for badge PRs.

    Merges badge-outreach.json tools with prebuilt-scans.json entries
    that have GitHub URLs, so we can PR repos even if badge-outreach
    only has website URLs.
    """
    tools = []

    # Load badge outreach data
    if BADGE_OUTREACH_PATH.exists():
        with open(BADGE_OUTREACH_PATH) as f:
            data = json.load(f)
        if isinstance(data, dict):
            tools = data.get("tools", [])
        elif isinstance(data, list):
            tools = data
    else:
        logger.warning("Badge outreach file not found: %s", BADGE_OUTREACH_PATH)

    # Also scan prebuilt-scans for tools with GitHub URLs
    # that meet the score threshold (enriches the candidate pool)
    scan_paths = [
        PROJECT_ROOT / "frontend" / "public" / "data" / "prebuilt-scans.json",
        PROJECT_ROOT / "data" / "prebuilt-scans.json",
    ]
    seen_ids = {t.get("scan_id") for t in tools if t.get("scan_id")}

    for path in scan_paths:
        if not path.exists():
            continue
        try:
            with open(path) as f:
                scans = json.load(f)
            if not isinstance(scans, list):
                continue
            for scan in scans:
                scan_id = scan.get("scan_id", "")
                if scan_id in seen_ids:
                    continue
                url = scan.get("url", "")
                if "github.com" in url and scan.get("clarvia_score", 0) >= 70:
                    tools.append({
                        "service_name": scan.get("service_name", ""),
                        "scan_id": scan_id,
                        "score": scan.get("clarvia_score", 0),
                        "url": url,
                        "badge_snippets": {},
                    })
                    seen_ids.add(scan_id)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Error loading %s: %s", path, e)
        break  # only need first available

    return tools


def normalize_repo(repo: str) -> str:
    """Normalize repo string: strip fragments, lowercase."""
    repo = re.sub(r"[#?].*$", "", repo)  # strip #readme, ?tab=... etc.
    return repo.strip("/").lower()


def load_submitted_repos() -> set[str]:
    """Load set of repo owner/name that already have PR submissions."""
    submitted = set()
    if not BADGE_PRS_PATH.exists():
        return submitted

    with open(BADGE_PRS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                repo = entry.get("repo", "")
                if repo:
                    submitted.add(normalize_repo(repo))
            except json.JSONDecodeError:
                continue
    return submitted


def append_pr_log(entry: dict) -> None:
    """Append a PR submission log entry to badge-prs.jsonl."""
    BADGE_PRS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BADGE_PRS_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def extract_github_repo(url: str) -> Optional[str]:
    """Extract owner/repo from a GitHub URL.

    Examples:
      https://github.com/owner/repo -> owner/repo
      https://github.com/owner/repo/tree/main -> owner/repo
    """
    if not url:
        return None

    patterns = [
        r"github\.com/([^/]+/[^/]+?)(?:\.git)?(?:[/#?]|$)",
        r"github\.com/([^/#?\s]+/[^/#?\s]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            repo = match.group(1).rstrip("/")
            # Remove trailing .git or other suffixes
            repo = re.sub(r"\.git$", "", repo)
            # Skip if it looks like a file path or too many segments
            if "/" in repo and repo.count("/") == 1:
                return repo
    return None


def check_repo_has_readme(repo: str) -> Optional[str]:
    """Check if repo has a README and return its content, or None."""
    content = run_gh(["api", f"repos/{repo}/readme", "--jq", ".content"], timeout=15)
    if content is None:
        return None

    # GitHub API returns base64-encoded content
    import base64
    try:
        decoded = base64.b64decode(content).decode("utf-8")
        return decoded
    except Exception:
        return None


def get_readme_path(repo: str) -> Optional[str]:
    """Get the actual README filename from repo (README.md, readme.md, etc.)."""
    result = run_gh(["api", f"repos/{repo}/readme", "--jq", ".name"], timeout=15)
    return result if result else "README.md"


def build_badge_section(tool: dict) -> str:
    """Build the badge markdown section to insert into README."""
    snippets = tool.get("badge_snippets", {})
    markdown_linked = snippets.get("markdown_linked", "")

    if not markdown_linked:
        # Build from scratch
        scan_id = tool.get("scan_id", "")
        score = tool.get("score", 0)
        badge_url = f"https://clarvia.art/api/badge/{scan_id}.svg"
        report_url = f"https://clarvia.art/tool/{scan_id}"
        markdown_linked = f"[![Clarvia AEO Score](https://clarvia.art/api/badge/{scan_id}.svg)](https://clarvia.art/tool/{scan_id})"

    return markdown_linked


def insert_badge_into_readme(readme: str, badge_md: str) -> str:
    """Insert badge markdown into README, after the title or at the top."""
    lines = readme.split("\n")

    # Find the first heading line
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_idx = i + 1
            # Skip any blank lines or existing badges right after title
            while insert_idx < len(lines) and (
                lines[insert_idx].strip() == ""
                or lines[insert_idx].strip().startswith("![")
                or lines[insert_idx].strip().startswith("[![")
            ):
                insert_idx += 1
            break

    # Don't duplicate if badge already exists
    if "clarvia" in readme.lower():
        return readme

    # Insert badge with surrounding blank lines
    lines.insert(insert_idx, "")
    lines.insert(insert_idx + 1, badge_md)
    lines.insert(insert_idx + 2, "")

    return "\n".join(lines)


def create_badge_issue(repo: str, tool: dict, log_entry: dict) -> dict:
    """Fallback: create a GitHub Issue suggesting badge addition (no fork needed)."""
    score = tool.get("score", 0)
    tool_name = tool.get("service_name", repo.split("/")[-1])
    scan_id = tool.get("scan_id", "")
    badge_md = tool.get("badge_snippets", {}).get("markdown_linked", "")
    if not badge_md and scan_id:
        badge_md = f"[![Clarvia AEO Score](https://clarvia.art/api/badge/{scan_id}.svg)](https://clarvia.art/tool/{scan_id})"

    title = f"Add Clarvia AEO Score badge ({score}/100) to README"
    body = (
        f"Hi! 👋\n\n"
        f"I wanted to let you know that **{tool_name}** has been reviewed on "
        f"[Clarvia](https://clarvia.art) and scored **{score}/100** for agent-readiness "
        f"(MCP compatibility, structured output, documentation quality, etc.).\n\n"
        f"You can add the badge to your README with this one-liner:\n\n"
        f"```markdown\n{badge_md}\n```\n\n"
        f"It dynamically updates as your score improves. Feel free to close if you're not interested — no hard feelings!\n\n"
        f"[View full report →](https://clarvia.art/tool/{scan_id})"
    )

    # Check if repo has issues enabled
    repo_info = run_gh(["api", f"repos/{repo}", "--jq", ".has_issues"], timeout=10)
    if repo_info != "true":
        log_entry["status"] = "skipped"
        log_entry["error"] = "Issues disabled on repo"
        return log_entry

    # Check for existing Clarvia issue
    existing = run_gh([
        "issue", "list", "--repo", repo,
        "--search", "Clarvia AEO", "--json", "number", "--jq", "length"
    ], timeout=15)
    if existing and existing.strip() != "0":
        log_entry["status"] = "skipped"
        log_entry["error"] = "Clarvia issue already exists"
        return log_entry

    result = run_gh([
        "issue", "create",
        "--repo", repo,
        "--title", title,
        "--body", body,
    ], timeout=30)

    if result and ("github.com" in result or "issues" in result):
        log_entry["status"] = "issue_submitted"
        log_entry["pr_url"] = result.strip()
        log_entry["type"] = "issue"
        logger.info("Issue created: %s", result.strip())
    else:
        log_entry["status"] = "failed"
        log_entry["error"] = f"Issue creation returned: {result}"

    return log_entry


def create_badge_pr(repo: str, tool: dict, dry_run: bool = False, issue_only: bool = False) -> dict:
    """Fork repo, add badge to README, create PR. Returns log entry."""
    ts = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "ts": ts,
        "repo": repo,
        "tool_name": tool.get("service_name", ""),
        "scan_id": tool.get("scan_id", ""),
        "score": tool.get("score", 0),
        "status": "pending",
        "pr_url": None,
        "error": None,
    }

    if dry_run:
        log_entry["status"] = "dry_run"
        logger.info("[DRY RUN] Would create badge PR for %s", repo)
        return log_entry

    if issue_only:
        logger.info("Issue-only mode: creating Issue for %s", repo)
        return create_badge_issue(repo, tool, log_entry)

    try:
        # Step 1: Fork the repo (with issue fallback)
        logger.info("Forking %s...", repo)
        fork_result = run_gh(["repo", "fork", repo, "--clone=false"], timeout=30)
        fork_blocked = fork_result is None

        if fork_blocked:
            logger.info("Fork blocked for %s — falling back to Issue outreach", repo)
            return create_badge_issue(repo, tool, log_entry)

        time.sleep(2)  # Give GitHub time to process the fork

        # Step 2: Get README content via API
        readme_path = get_readme_path(repo)
        readme_content = check_repo_has_readme(repo)
        if readme_content is None:
            log_entry["status"] = "failed"
            log_entry["error"] = "No README found"
            return log_entry

        # Step 3: Build badge section
        badge_md = build_badge_section(tool)
        updated_readme = insert_badge_into_readme(readme_content, badge_md)

        if updated_readme == readme_content:
            log_entry["status"] = "skipped"
            log_entry["error"] = "Badge already present in README"
            return log_entry

        # Step 4: Create branch and commit via GitHub API
        # Get default branch SHA
        default_branch_info = run_gh([
            "api", f"repos/{GITHUB_AUTHOR}/{repo.split('/')[-1]}",
            "--jq", ".default_branch"
        ], timeout=15)
        default_branch = default_branch_info or "main"

        # Get the SHA of the default branch head
        ref_info = run_gh([
            "api", f"repos/{GITHUB_AUTHOR}/{repo.split('/')[-1]}/git/ref/heads/{default_branch}",
            "--jq", ".object.sha"
        ], timeout=15)
        if not ref_info:
            log_entry["status"] = "failed"
            log_entry["error"] = "Could not get default branch SHA from fork"
            return log_entry

        # Create branch on our fork
        import base64
        create_branch = run_gh([
            "api", f"repos/{GITHUB_AUTHOR}/{repo.split('/')[-1]}/git/refs",
            "--method", "POST",
            "--field", f"ref=refs/heads/{BRANCH_NAME}",
            "--field", f"sha={ref_info}",
        ], timeout=15)
        if create_branch is None:
            # Branch might already exist, try to update it
            logger.info("Branch %s may already exist, trying to update...", BRANCH_NAME)

        # Step 5: Update README on our fork's branch
        # Get current file SHA
        file_info = run_gh([
            "api", f"repos/{GITHUB_AUTHOR}/{repo.split('/')[-1]}/contents/{readme_path}",
            "--jq", ".sha",
            "-H", f"ref: {BRANCH_NAME}",
        ], timeout=15)

        # If branch didn't have the file, try default branch
        if not file_info:
            file_info = run_gh([
                "api", f"repos/{GITHUB_AUTHOR}/{repo.split('/')[-1]}/contents/{readme_path}",
                "--jq", ".sha",
            ], timeout=15)

        if not file_info:
            log_entry["status"] = "failed"
            log_entry["error"] = "Could not get README file SHA"
            return log_entry

        encoded_content = base64.b64encode(updated_readme.encode("utf-8")).decode("ascii")
        commit_result = run_gh([
            "api", f"repos/{GITHUB_AUTHOR}/{repo.split('/')[-1]}/contents/{readme_path}",
            "--method", "PUT",
            "--field", f"message=Add Clarvia AEO Score badge",
            "--field", f"content={encoded_content}",
            "--field", f"sha={file_info}",
            "--field", f"branch={BRANCH_NAME}",
        ], timeout=30)

        if commit_result is None:
            log_entry["status"] = "failed"
            log_entry["error"] = "Failed to commit README update"
            return log_entry

        # Step 6: Create PR
        score = tool.get("score", 0)
        tool_name = tool.get("service_name", repo.split("/")[-1])
        pr_title = f"Add Clarvia AEO Score badge ({score}/100)"
        pr_body = (
            f"## Clarvia AEO Score Badge\n\n"
            f"This PR adds a [Clarvia](https://clarvia.art) AEO (Agent Experience Optimization) "
            f"Score badge to the README.\n\n"
            f"**{tool_name}** scored **{score}/100** on Clarvia's automated assessment.\n\n"
            f"The badge dynamically updates as the tool's score changes.\n\n"
            f"### What is Clarvia?\n\n"
            f"Clarvia scans and rates AI agent tools (MCP servers, CLI tools, skills) "
            f"for agent-readiness — structured output, error handling, documentation quality, "
            f"and more. Think of it as a quality signal for the AI tool ecosystem.\n\n"
            f"Feel free to reject this PR if you don't want the badge. No hard feelings!"
        )

        pr_result = run_gh([
            "pr", "create",
            "--repo", repo,
            "--head", f"{GITHUB_AUTHOR}:{BRANCH_NAME}",
            "--title", pr_title,
            "--body", pr_body,
        ], timeout=30)

        if pr_result and ("github.com" in pr_result or "pull" in pr_result):
            log_entry["status"] = "submitted"
            log_entry["pr_url"] = pr_result.strip()
            logger.info("PR created: %s", pr_result.strip())
        else:
            log_entry["status"] = "failed"
            log_entry["error"] = f"PR creation returned: {pr_result}"

    except Exception as e:
        log_entry["status"] = "failed"
        log_entry["error"] = str(e)
        logger.exception("Error creating badge PR for %s", repo)

    return log_entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-submit Clarvia badge PRs")
    parser.add_argument("--limit", type=int, default=3, help="Max PRs per run (default: 3)")
    parser.add_argument("--min-score", type=int, default=70, help="Minimum score threshold (default: 70)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't create PRs")
    parser.add_argument("--issue-only", action="store_true", help="Skip fork/PR, go straight to Issue outreach")
    args = parser.parse_args()

    logger.info("=== Auto Badge PR Submission ===")
    logger.info("Limit: %d | Min score: %d | Dry run: %s", args.limit, args.min_score, args.dry_run)

    # Verify gh CLI is authenticated
    if not args.dry_run:
        auth_check = run_gh(["auth", "status"], timeout=10)
        if auth_check is None:
            logger.error("gh CLI not authenticated. Run: gh auth login")
            sys.exit(1)

    # Load data
    tools = load_badge_outreach()
    submitted = load_submitted_repos()

    logger.info("Loaded %d eligible tools, %d already submitted", len(tools), len(submitted))

    # Filter: must have GitHub URL, not already submitted, meets score threshold
    candidates = []
    for tool in tools:
        url = tool.get("url", "")
        github_url = tool.get("github_url", url)
        repo = extract_github_repo(github_url)

        if not repo:
            continue

        if normalize_repo(repo) in submitted:
            logger.debug("Skipping %s (already submitted)", repo)
            continue

        score = tool.get("score", 0)
        if score < args.min_score:
            continue

        # Don't PR our own repos
        if repo.lower().startswith(f"{GITHUB_AUTHOR.lower()}/"):
            continue

        candidates.append((repo, tool))

    logger.info("Found %d candidates after filtering", len(candidates))

    # Process up to limit
    submitted_count = 0
    issue_count = 0
    for repo, tool in candidates[:args.limit]:
        logger.info("Processing: %s (score: %d)", repo, tool.get("score", 0))

        log_entry = create_badge_pr(repo, tool, dry_run=args.dry_run, issue_only=args.issue_only)
        append_pr_log(log_entry)

        if log_entry["status"] == "submitted":
            submitted_count += 1
        elif log_entry["status"] == "issue_submitted":
            issue_count += 1

        if log_entry["status"] in ("submitted", "issue_submitted", "dry_run"):
            time.sleep(PR_DELAY_SECONDS)

    logger.info("=== Done: %d PRs + %d Issues submitted ===", submitted_count, issue_count)


if __name__ == "__main__":
    main()
