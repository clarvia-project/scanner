#!/usr/bin/env python3
"""Auto-merge catalog and push to trigger deploy.

Workflow:
  1. Run merge_catalog.py to consolidate all data files
  2. Check if data/prebuilt-scans.json changed (new tools added)
  3. If changed: git add + commit + push to origin/main
  4. The push triggers deploy-on-push.yml (tests -> Render deploy)
  5. If unchanged: do nothing

Designed to run daily at 8am, after the harvester (6am), classifier (6:30am),
and data auditor (7am) have finished processing new entries.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MERGE_SCRIPT = PROJECT_ROOT / "scripts" / "merge_catalog.py"
CATALOG_PATH = PROJECT_ROOT / "data" / "prebuilt-scans.json"
BACKEND_CATALOG = PROJECT_ROOT / "backend" / "data" / "prebuilt-scans.json"


def run_cmd(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd or PROJECT_ROOT),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def count_catalog_entries(path: Path) -> int:
    """Count entries in the catalog JSON file."""
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            return sum(len(v) for v in data.values() if isinstance(v, list))
    except (json.JSONDecodeError, OSError):
        pass
    return 0


def main() -> int:
    # Step 1: Get pre-merge count
    count_before = count_catalog_entries(CATALOG_PATH)
    logger.info("Catalog before merge: %d entries", count_before)

    # Step 2: Run merge_catalog.py
    logger.info("Running merge_catalog.py...")
    rc, stdout, stderr = run_cmd([sys.executable, str(MERGE_SCRIPT)])
    if rc != 0:
        logger.error("merge_catalog.py failed (exit %d): %s", rc, stderr[:500])
        return 1
    if stdout:
        logger.info("merge output: %s", stdout[:300])

    # Step 3: Check for changes
    count_after = count_catalog_entries(CATALOG_PATH)
    new_tools = count_after - count_before
    logger.info("Catalog after merge: %d entries (%+d)", count_after, new_tools)

    # Check git status for actual file changes
    rc, diff_out, _ = run_cmd(
        ["git", "diff", "--name-only", "--", "data/prebuilt-scans.json", "backend/data/prebuilt-scans.json"]
    )
    if rc != 0 or not diff_out.strip():
        # Also check untracked
        rc2, status_out, _ = run_cmd(["git", "status", "--porcelain", "--", "data/prebuilt-scans.json"])
        if rc2 != 0 or not status_out.strip():
            logger.info("No catalog changes detected — nothing to deploy")
            return 0

    logger.info("Catalog changed — committing and pushing")

    # Step 4: Git add + commit + push
    files_to_add = []
    for f in [CATALOG_PATH, BACKEND_CATALOG]:
        if f.exists():
            files_to_add.append(str(f.relative_to(PROJECT_ROOT)))

    if not files_to_add:
        logger.warning("No catalog files found to commit")
        return 0

    rc, _, err = run_cmd(["git", "add"] + files_to_add)
    if rc != 0:
        logger.error("git add failed: %s", err)
        return 1

    # Check if there's actually something staged
    rc, staged, _ = run_cmd(["git", "diff", "--cached", "--name-only"])
    if not staged.strip():
        logger.info("Nothing staged after git add — no real changes")
        return 0

    commit_msg = f"chore: auto-merge catalog — {new_tools} new tools" if new_tools > 0 else "chore: auto-merge catalog refresh"
    rc, _, err = run_cmd(["git", "commit", "-m", commit_msg])
    if rc != 0:
        logger.error("git commit failed: %s", err)
        return 1
    logger.info("Committed: %s", commit_msg)

    rc, _, err = run_cmd(["git", "push", "origin", "main"])
    if rc != 0:
        logger.error("git push failed: %s", err)
        return 1

    logger.info("Pushed to origin/main — deploy-on-push workflow will handle deployment")

    # Step 5: Trigger Render deploy hook as backup (in case auto-deploy misses the push)
    deploy_hook = os.environ.get("RENDER_DEPLOY_HOOK_URL", "")
    if deploy_hook:
        import urllib.request
        try:
            with urllib.request.urlopen(urllib.request.Request(deploy_hook, method="POST"), timeout=10) as resp:
                logger.info("Render deploy hook triggered (status %d)", resp.status)
        except Exception as e:
            logger.warning("Render deploy hook failed (non-fatal): %s", e)
    else:
        logger.info("RENDER_DEPLOY_HOOK_URL not set — relying on GitHub auto-deploy only")

    return 0


if __name__ == "__main__":
    sys.exit(main())
