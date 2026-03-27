# Arbiter Report — Scoring System Overhaul

**Arbiter**: Scoring Arbiter Agent
**Date**: 2026-03-27

---

## Round 2 — Distribution Tuning

### Target vs Achieved

| Type | Target Strong% | Round 1 Strong% | Round 2 Strong% | Status |
|------|---------------|-----------------|-----------------|--------|
| MCP Server | 5-10% | 3.8% | **5.9%** | MET |
| API | 20-30% | 20.7% | **20.7%** | MET (unchanged) |
| Connector | reasonable | 7.6% | **7.6%** | MET (unchanged) |
| CLI Tool | 3-8% | 0.4% | **3.1%** | MET |
| Skill | 2-5% | 3.7% | **3.7%** | MET (unchanged) |

### Full Distribution (all data)

| Type | N | Mean | Low% | Basic% | Moderate% | Strong% | Max |
|------|---|------|------|--------|-----------|---------|-----|
| MCP Server | 4,224 | 56.5 | 0.0% | 10.1% | 84.1% | 5.9% | 96 |
| API | 2,529 | 61.4 | 0.0% | 1.9% | 77.5% | 20.7% | 83 |
| Connector | 1,509 | 52.6 | 0.0% | 0.0% | 92.4% | 7.6% | 78 |
| CLI Tool | 3,687 | 44.5 | 2.5% | 47.6% | 46.8% | 3.1% | 82 |
| Skill | 900 | 50.7 | 0.0% | 26.4% | 69.9% | 3.7% | 81 |

---

## Round 2 Changes

### MCP Scorer (`mcp_scorer.py`)

**Problem**: 3.8% Strong, target 5-10%. 152 servers at 65-69 (near miss).

**Fix**: Increased completeness bonus tiers. Servers strong across multiple dimensions now get more credit, compensating for the structural limitation that registry data lacks tools/prompts/resources metadata.

| Tier | Before | After |
|------|--------|-------|
| 3+ dims ≥ 18 | +10 | +12 |
| 3+ dims ≥ 15 | +7 | +9 |
| 2 dims ≥ 15 + 3 dims ≥ 12 | +6 (new) | +8 |
| 3+ dims ≥ 12 | +4 | +6 |
| 2 dims ≥ 12 + 4 dims ≥ 10 | (new) | +4 |

**Result**: 162 → 251 Strong (3.8% → 5.9%)

### CLI Scorer (`cli_scorer.py`)

**Problem**: 0.4% Strong, target 3-8%. Root cause: `agent_integration` dimension averaged 3.5/25 — most CLI tools don't mention "json", "mcp", "machine-readable" in their npm descriptions, but are inherently agent-usable (accept args, return exit codes, produce capturable output).

**Fix 1 — Agent integration baseline (0-5 points)**:
- +3 for tools explicitly mentioning CLI signals (cli, command-line, terminal, etc.)
- +2 for tools with install commands (installable = runnable by agent)
- +1 baseline for all registered CLI tools
- +2 bonus for global install (npx, -g, pipx) — easier for agents

**Fix 2 — Broadened signal keywords**:
- Machine-readable output: added "output", "format", "export", "report", "table"
- Scriptability: added "transform", "convert", "parse", "generate", "compile", "lint", "test", "check", "validate", "run", "execute"

**Fix 3 — Asymmetric completeness bonus**:
Since `agent_integration` is structurally harder to score from metadata, the bonus now also considers just the other 3 dimensions (usability, documentation, ecosystem):

| Tier | Bonus |
|------|-------|
| 3+ all dims ≥ 15 | +10 |
| 3 other dims ≥ 15 | +9 |
| 2 all dims ≥ 15 + 3 ≥ 12 | +9 |
| 2 other dims ≥ 15 + 3 other ≥ 12 | +8 |
| 3+ all dims ≥ 12 | +5 |
| 3 other dims ≥ 12 | +4 |

**Result**: 15 → 114 Strong (0.4% → 3.1%)

---

## Round 1 Changes (from initial review)

### New Files Created
1. **`connector_scorer.py`** — Dedicated scorer for n8n/Zapier/Composio connectors (was previously routed through api_scorer and getting crushed)
2. **`__init__.py`** — Unified entry point with `score_tool()` auto-detection and routing
3. **`test_scorers.py`** — Distribution test against real data (20 samples per type, `--full` for all)

### Fixes Applied from Review

| Priority | Issue | Fix |
|----------|-------|-----|
| P0 | n8n connectors scoring 90% Low | Created `connector_scorer.py` with service-tier recognition |
| P1 | MCP score range compressed (29-62) | Increased `tool_quality` baseline when tools metadata unavailable (2→4 for servers with packages/remotes) |
| P1 | API spec_quality + reliability_trust double-counting source bonus | Reduced spec_quality source bonus from 0-4 to 0-2 |
| P2 | Homebrew tools missing from cli_scorer source_points | Added `"homebrew": 3` |
| P2 | api_scorer `_score_documentation` not using actual title field | Added `title` parameter, use `display_title = title or name` |
| P2 | No penalty for non-active MCP registry status | Added -2 penalty for inactive/deprecated status |
| P2 | CLI MCP double-counting in agent_integration | Only award MCP wrapper bonus when agent_keywords didn't already match |

### Not Fixed (Deliberate)
- **skill_scorer scope_safety is mostly a popularity proxy**: True, but we don't have real permission/safety metadata from GitHub. Stars + org backing is the best proxy available.
- **Schema version hardcoded in mcp_scorer**: Low risk — schema versions change rarely.

---

## Before → After (End-to-End)

| Type | Old Monolithic Mean | Old Strong% | New Mean | New Strong% |
|------|-------------------|-------------|----------|-------------|
| MCP | 73.3 | 67% | 56.5 | 5.9% |
| API | 65.5 | 26% | 61.4 | 20.7% |
| Connector | 30.9 | 0% | 52.6 | 7.6% |
| CLI | 67.5 | 60% | 44.5 | 3.1% |
| Skill | N/A | N/A | 50.7 | 3.7% |

The old monolithic scorer severely inflated MCP/CLI (60-67% Strong) while crushing connectors (0% Moderate). The new type-specific system produces realistic distributions where Strong is reserved for genuinely excellent tools.

### API Strong% Note
20.7% Strong for APIs: 99.5% of Strong APIs are tier-1 providers (Google, Azure, AWS, Stripe, etc.). These genuinely deserve high scores. Unknown providers score Moderate at best.

---

## Architecture

```
scoring/
  __init__.py          # score_tool() — unified entry point
  mcp_scorer.py        # score_mcp_server() — 4 dims × 25 pts
  api_scorer.py        # score_api() — 4 dims × 25 pts
  connector_scorer.py  # score_connector() — 4 dims × 25 pts
  cli_scorer.py        # score_cli_tool() — 4 dims × 25 pts
  skill_scorer.py      # score_skill() — 4 dims × 25 pts
  test_scorers.py      # Distribution validation
```

### Type Detection Priority
1. Has `server` key → `mcp_server`
2. Explicit `type` field → use as-is
3. Source-based: `apis_guru`/`composio` → `api`, `n8n` → `connector`, `npm`/`homebrew` → `cli_tool`
4. Fallback → `general` (uses api_scorer)

### Standardized Output
```python
{
    "clarvia_score": int,     # 0-100
    "rating": str,            # "Strong" | "Moderate" | "Basic" | "Low"
    "dimensions": {
        "<name>": {"score": int, "max": 25, ...}
    },
    "tool_type": str          # "mcp_server" | "api" | "connector" | "cli_tool" | "skill"
}
```

---

## Code Style Consistency Check

All 5 scorers follow:
- Same rating thresholds: Strong ≥ 70, Moderate ≥ 45, Basic ≥ 25, Low < 25
- Same output format: `{clarvia_score, rating, dimensions}`
- Same 4 × 25 dimensional structure
- Same min() capping per dimension
- Private `_score_*` helper functions
- Type hints throughout
- Docstrings with sub-factor documentation
