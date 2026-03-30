#!/usr/bin/env bash
# submit_to_directories.sh — Fork awesome-mcp-servers repos, add Clarvia entry, create PRs
#
# Usage:
#   ./scripts/submit_to_directories.sh           # Execute for real
#   ./scripts/submit_to_directories.sh --dry-run  # Preview what would happen
#
# Prerequisites:
#   - gh CLI installed and authenticated (gh auth login)
#   - git installed
#
# Manual submission (if gh CLI is not available):
#   1. Go to https://github.com/wong2/awesome-mcp-servers → Fork
#   2. Clone your fork locally
#   3. Create branch: git checkout -b add-clarvia
#   4. Add the entry from submissions/pr-ready/awesome-mcp-wong2.md to README.md
#      under the "Developer Tools" section
#   5. Commit: git commit -am "Add Clarvia - AEO scoring and tool discovery for AI agents"
#   6. Push: git push origin add-clarvia
#   7. Create PR on GitHub from your fork
#   8. Repeat for https://github.com/appcypher/awesome-mcp-servers

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "=== DRY RUN MODE — no changes will be made ==="
  echo ""
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WORK_DIR=$(mktemp -d)
BRANCH_NAME="add-clarvia"
COMMIT_MSG="Add Clarvia - AEO scoring and tool discovery for AI agents"

# Clarvia entry for wong2/awesome-mcp-servers format
WONG2_ENTRY='- **[Clarvia](https://github.com/clarvia-project/scanner)** - AEO scoring and tool discovery platform for AI agents. Search 12,800+ indexed MCP servers, APIs, and CLIs with agent-readiness scores, gate-check tools before use, compare alternatives, and submit quality feedback.'

# Clarvia entry for appcypher/awesome-mcp-servers format
APPCYPHER_ENTRY='- <img src="https://clarvia.art/favicon.ico" height="14"/> [Clarvia](https://github.com/clarvia-project/scanner) - AEO scoring and tool discovery platform for AI agents — search 12,800+ indexed tools, gate-check services before use, compare alternatives, and submit quality feedback'

PR_BODY="$(cat <<'PREOF'
## What is Clarvia?

[Clarvia](https://clarvia.art) is an AEO (Agent Engine Optimization) scoring and tool discovery platform. It indexes 12,800+ AI agent tools (MCP servers, APIs, CLIs) and scores them on agent-readiness (0-100).

**16 MCP tools** including search, scan, gate-check, batch-check, alternatives, live probe, feedback, setup benchmarking, and issue tracking.

**Install:**
```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["clarvia-mcp-server"]
    }
  }
}
```

- npm: https://www.npmjs.com/package/clarvia-mcp-server
- Website: https://clarvia.art
- GitHub: https://github.com/clarvia-project/scanner
PREOF
)"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

check_prerequisites() {
  if ! command -v gh &> /dev/null; then
    echo "ERROR: gh CLI not found. Install it from https://cli.github.com/"
    echo ""
    echo "Alternatively, follow the manual submission steps at the top of this script."
    exit 1
  fi

  if ! gh auth status &> /dev/null; then
    echo "ERROR: gh CLI not authenticated. Run: gh auth login"
    exit 1
  fi

  echo "Prerequisites OK: gh CLI installed and authenticated."
  echo ""
}

submit_to_repo() {
  local OWNER="$1"
  local REPO="$2"
  local ENTRY="$3"
  local SECTION_MARKER="$4"

  echo "=========================================="
  echo "Submitting to $OWNER/$REPO"
  echo "=========================================="

  if $DRY_RUN; then
    echo "[DRY RUN] Would fork $OWNER/$REPO"
    echo "[DRY RUN] Would create branch: $BRANCH_NAME"
    echo "[DRY RUN] Would add entry after section: $SECTION_MARKER"
    echo "[DRY RUN] Entry:"
    echo "  $ENTRY"
    echo "[DRY RUN] Would commit with message: $COMMIT_MSG"
    echo "[DRY RUN] Would create PR titled: $COMMIT_MSG"
    echo ""
    return 0
  fi

  # Fork the repo (idempotent — if already forked, gh returns existing fork)
  echo "Forking $OWNER/$REPO..."
  gh repo fork "$OWNER/$REPO" --clone=false 2>/dev/null || true

  # Get the authenticated user's GitHub username
  GH_USER=$(gh api user -q '.login')
  FORK_URL="https://github.com/$GH_USER/$REPO.git"

  # Clone the fork
  echo "Cloning fork to $WORK_DIR/$REPO..."
  git clone --depth 1 "$FORK_URL" "$WORK_DIR/$REPO"
  cd "$WORK_DIR/$REPO"

  # Add upstream remote and fetch
  git remote add upstream "https://github.com/$OWNER/$REPO.git" 2>/dev/null || true
  git fetch upstream main --depth 1

  # Create branch from upstream main
  git checkout -b "$BRANCH_NAME" upstream/main

  # Add the entry to README.md
  # Strategy: find the section marker and append after the last entry in that section
  if grep -q "Clarvia" README.md; then
    echo "WARNING: Clarvia already exists in $OWNER/$REPO README.md. Skipping."
    cd "$PROJECT_DIR"
    return 0
  fi

  # Use Python for reliable file editing
  python3 -c "
import re, sys

with open('README.md', 'r') as f:
    content = f.read()

marker = '''$SECTION_MARKER'''
entry = '''$ENTRY'''

# Find the section and add entry at end of section's list
idx = content.find(marker)
if idx == -1:
    # Fallback: find any 'Developer Tools' or 'Testing' section
    for fallback in ['Developer Tools', 'Testing', '## Tools']:
        idx = content.find(fallback)
        if idx != -1:
            break

if idx == -1:
    print('ERROR: Could not find target section in README.md', file=sys.stderr)
    sys.exit(1)

# Find the end of the list items in this section (next ## heading or end of file)
section_start = idx
next_heading = content.find('\n## ', section_start + 1)
if next_heading == -1:
    next_heading = len(content)

# Find the last list item before the next heading
insert_pos = content.rfind('\n- ', section_start, next_heading)
if insert_pos == -1:
    insert_pos = content.rfind('\n|', section_start, next_heading)

if insert_pos == -1:
    print('ERROR: Could not find insertion point', file=sys.stderr)
    sys.exit(1)

# Find end of that line
line_end = content.find('\n', insert_pos + 1)
if line_end == -1:
    line_end = len(content)

# Insert after the last entry
new_content = content[:line_end] + '\n' + entry + content[line_end:]

with open('README.md', 'w') as f:
    f.write(new_content)

print('Entry added successfully.')
"

  # Commit and push
  git add README.md
  git commit -m "$COMMIT_MSG"
  git push origin "$BRANCH_NAME" --force

  # Create PR
  echo "Creating PR..."
  PR_URL=$(gh pr create \
    --repo "$OWNER/$REPO" \
    --head "$GH_USER:$BRANCH_NAME" \
    --title "$COMMIT_MSG" \
    --body "$PR_BODY" \
    2>&1)

  echo "PR created: $PR_URL"
  echo ""

  cd "$PROJECT_DIR"
}

# ---- Main ----

check_prerequisites

# 1. wong2/awesome-mcp-servers
submit_to_repo \
  "wong2" \
  "awesome-mcp-servers" \
  "$WONG2_ENTRY" \
  "Community Servers"

# 2. appcypher/awesome-mcp-servers
submit_to_repo \
  "appcypher" \
  "awesome-mcp-servers" \
  "$APPCYPHER_ENTRY" \
  "AI Services"

echo "=========================================="
echo "Done!"
if $DRY_RUN; then
  echo "(Dry run — no changes were made)"
else
  echo "Check the PR URLs above."
fi
echo "=========================================="
