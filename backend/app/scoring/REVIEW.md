# Scoring System Review

**Reviewer**: Scoring Reviewer Agent
**Date**: 2026-03-27
**Files reviewed**: `mcp_scorer.py`, `api_scorer.py`, `cli_scorer.py`, `skill_scorer.py`, `__init__.py`

---

## Overall Assessment: 7.5/10

The scoring system is well-structured with type-specific dimensions, clean separation, and a unified `__init__.py` router. All scorers run offline (no external API calls). However, there are **critical distribution problems** that need fixing before production use.

---

## Score Distribution (100-sample tests per type)

| Type | Min | P25 | Median | P75 | Max | Avg | Problem |
|------|-----|-----|--------|-----|-----|-----|---------|
| MCP Server | 26 | 45 | 47 | 50 | 65 | 47.1 | **Compressed range**, 0% Strong, 0% Low |
| API (apis_guru) | 46 | 53 | 63 | 72 | 82 | 63.5 | Skews high — 42% Strong |
| Connector (n8n) | 19 | 19 | 19 | 20 | 28 | 19.7 | **CRITICAL: 96% Low** |
| Skill | 29 | 40 | 45 | 53 | 61 | 45.6 | 0% Strong, decent spread |
| CLI Tool | 18 | 34 | 40 | 46 | 55 | 38.3 | 0% Strong, 22% Low |

---

## Critical Issues

### 1. n8n Connectors Score Near-Zero (CRITICAL)

**Problem**: n8n connectors have only 5 fields (`name`, `url`, `source`, `type`, `description`) but the `api_scorer` expects `openapi_url`, `homepage`, `version`, `title`, `category`. Result: 96% score "Low" (19-20 points).

**Root cause**: `api_scorer` gives heavy weight to OpenAPI spec (up to 8 pts in spec_quality), version (6 pts across dimensions), and homepage (6 pts in documentation). n8n connectors have none of these.

**Fix required**: Either:
- (A) Add a `connector_scorer.py` that scores based on n8n-specific signals (integration URL, name recognition, connector category), OR
- (B) Add connector-specific baselines in `api_scorer.py` — when `source == "n8n"`, grant baseline points for being a vetted integration platform (n8n curates these connectors). The `description` field is just "n8n integration: {name}" which is auto-generated and near-worthless for scoring.

**Recommended fix (B)**:
```python
# In _score_spec_quality, add early:
if source == "n8n" and not openapi_url:
    # n8n connectors are pre-built integrations, give baseline spec credit
    score += 8  # equivalent to having a spec — n8n handles the spec internally
```
Similar baselines needed in all 4 dimensions for n8n connectors.

### 2. MCP Scores Compressed to 26-65 Range (HIGH)

**Problem**: No MCP server scores "Strong" (70+) and none scores "Low" (<25). The effective range is only 39 points wide. This means the scorer cannot differentiate between excellent and mediocre MCP servers.

**Root cause**:
- `tool_quality` dimension maxes at ~7 because 0% of registry entries have `tools` populated. The scorer correctly handles this with implied-tooling fallback, but the fallback ceiling is too low (2 pts for implied, vs 8 pts max).
- `integration_readiness` has good spread (0-16 observed), this dimension works well.
- `trust_ecosystem` clusters around 10-18 due to all entries being in the official registry (automatic 3-5 pts).

**Fix**: Increase the ceiling for entries without `tools` metadata. Since tools aren't populated in the registry dump, the current scoring effectively penalizes ALL entries equally. Suggested: when `tool_count == 0` and the server has packages/remotes, grant 4 base points (it's a working server, just no tool metadata).

### 3. API Scores Skew High (MEDIUM)

**Problem**: apis_guru entries average 63.5 with 42% scoring "Strong". This is because apis_guru entries inherently have `openapi_url` (free 6-8 pts in spec_quality + 5 pts in documentation + 1 pt in agent_friendliness = 12-14 free points).

**Fix**: Reduce the automatic OpenAPI bonus or raise the "Strong" threshold for APIs to 75. The OpenAPI presence should be the baseline expectation for APIs, not a differentiator.

---

## Per-Scorer Detailed Review

### mcp_scorer.py — 8/10

**Strengths**:
- Excellent data shape documentation in docstring with actual registry stats
- Handles missing fields gracefully (tools=0 fallback, empty remotes/packages)
- Well-calibrated sub-factor weights within dimensions
- `WELL_KNOWN_ORGS`, `REGISTRY_TIERS`, `TRANSPORT_SCORES` constants are clean
- Returns `details` dicts for debugging/transparency

**Issues**:
1. **`_score_tool_quality` ceiling too low** — When tools=0 (100% of current data), max tool_count_score is 2. Combined with schema_score=0 and prompts_resources_score=0, this dimension maxes at ~14/25 even for the best entries. The description_quality sub-factor does the heavy lifting alone.
2. **Schema version hardcoded** — `"2025-12-11"` and `"2025-09-29"` in `_score_documentation_discovery` will need updating when new schema versions release. Consider comparing dates instead.
3. **No penalty for `status != "active"`** — The scorer gives 0 bonus for non-active status but doesn't deduct. An "inactive" or "deprecated" server should score lower.

**Field name accuracy**: All field names match the actual data (`server.name`, `server.packages[].registryType`, `_meta.io.modelcontextprotocol.registry/official.updatedAt`, etc.). Correct.

### api_scorer.py — 7/10

**Strengths**:
- Comprehensive provider tier system (Tier 1/2/3)
- Auth type detection with ranked scoring is smart
- Handles both apis_guru and n8n sources
- `_detect_spec_version` is clever URL-based inference

**Issues**:
1. **n8n connectors get crushed** (see Critical Issue #1)
2. **`_score_agent_friendliness` relies too much on description text** — Rate limits, pagination, error format are rarely mentioned in API descriptions. This means most APIs score 0-4 on these sub-factors regardless of actual quality. Consider giving partial credit when `openapi_url` exists (specs typically define these).
3. **`_is_slug_only` has a bug** — `"." not in name` means domain-style names like `"stripe.com"` are NOT considered slug-only (correct), but `"my-api"` IS slug-only (also correct). However, `"my.api"` returns False even though it's still slug-like. Minor.
4. **`_get_provider_tier` does double work** — First splits name into parts and checks each, then checks substrings of the whole name. The substring check makes the split check redundant for most cases. Not a bug, just inefficient.
5. **`_score_documentation` line 392**: `title = name` — This uses the `name` parameter (which is `tool.get("name")`) as a title proxy, but the actual `title` field from the data is never passed to this function. Should use `tool.get("title")` instead.

**Field name accuracy**: All field references (`name`, `title`, `description`, `version`, `url`, `homepage`, `openapi_url`, `source`, `category`, `type`) match the actual data. Correct.

### cli_scorer.py — 8/10

**Strengths**:
- Clean four-dimension structure with equal 25-point weights
- Good handling of multiple package managers (npm, pip, brew, cargo, go)
- `_score_ecosystem` uses both stars and npm_score with appropriate fallback
- `updated_at` recency scoring is well-calibrated

**Issues**:
1. **Homebrew tools underscored** — Homebrew entries lack `keywords`, `repository` (as string), `npm_url`, and `stars`. They only have `name`, `description`, `homepage`, `version`, `source`, `type`, `install_command`. This means they miss points in documentation (no npm_url, no repo), ecosystem (no stars, no npm_score), and agent_integration (no keywords to match against). Average homebrew score: ~21-25.
2. **`_score_agent_integration` MCP double-counting** — Line 138 checks `"mcp" in name or "mcp" in kw_lower` for +4 points, but lines 124-128 already count "mcp" as an agent_keyword for +2 points. An MCP tool gets +6 just for having "mcp" in the name.
3. **Skills scored by cli_scorer lose points** — When `detect_tool_type` routes a skill here (shouldn't happen normally due to explicit type), the usability dimension penalizes skills for lacking `install_command`. Not a real issue since routing works correctly.
4. **`source` field for homebrew = "homebrew"** but `source_points` dict doesn't include it, so it falls to default 1. Should add `"homebrew": 2`.

**Field name accuracy**: Correctly handles both `keywords` (npm) and `topics` (github) via `tool.get("keywords") or tool.get("topics")`. All other fields match. Correct.

### skill_scorer.py — 7/10

**Strengths**:
- Good prompt quality analysis with action verb detection
- Name-description alignment check is a nice quality signal
- Platform compatibility multi-matching across Claude/OpenAI/Cursor/Copilot
- Stars as community trust proxy is well-calibrated

**Issues**:
1. **`_score_scope_safety` is mostly a popularity proxy** — 12 of 25 points come from stars (7 pts) and org name (5 pts). The actual "scope & safety" signals (sandbox, permission, restricted keywords) are unlikely to appear in GitHub descriptions. This dimension doesn't truly measure safety.
2. **`_score_scope_safety` line 139**: `if 5 <= len(desc_words) <= 30: score += 2` — This rewards short descriptions as "well-scoped", but many poor-quality entries also have short descriptions. A 5-word description like "best agent harness" gets +2 for being "concise".
3. **`_score_integration` gives 0 points for platform compatibility** when no agent-related keywords appear in description/topics. Many valid skills (e.g., code formatters, linters) are platform-agnostic but still useful. Consider a small baseline.
4. **No `full_name` fallback** — `_score_scope_safety` checks `full_name` for org matching, but `_score_prompt_quality` and others don't use it. Inconsistent.
5. **Skills with 0 stars and no org** score only 2/25 in scope_safety (just the concise-desc bonus). This dimension should have more metadata-based signals.

**Field name accuracy**: Correctly uses `topics` (GitHub skills), `stars`, `full_name`, `language`, `updated_at`, `homepage`. All match actual data. Correct.

### __init__.py — 9/10

**Strengths**:
- Clean auto-detection logic with clear priority order
- `detect_tool_type` covers all data sources correctly
- Unified `score_tool` interface is easy to use
- Adds `tool_type` to result for transparency

**Issues**:
1. **`connector` routes to `score_api`** — This is the source of the n8n connector problem. Should either route to a dedicated connector scorer or apply connector-specific adjustments before/after calling `score_api`.
2. **`general` fallback uses `score_api`** — For unknown tool types, API scorer may not be the best default. Consider a minimal scorer that just checks basic signals (name, description, URL presence).

---

## Missing Fields Handling Summary

| Scorer | Missing fields handled? | Edge cases |
|--------|------------------------|------------|
| mcp_scorer | Yes — tools=0 fallback, empty packages/remotes/meta | Good |
| api_scorer | Partial — n8n connectors missing 5+ fields | **Needs fix** |
| cli_scorer | Yes — falls back gracefully for missing keywords/stars | Homebrew slightly penalized |
| skill_scorer | Yes — handles missing topics, stars, homepage | Good |

## Weight Balance Summary

| Scorer | Dominant dimension? | Assessment |
|--------|-------------------|------------|
| mcp_scorer | integration_readiness (0-16 range) | Acceptable — this IS the key differentiator for MCP |
| api_scorer | spec_quality + reliability_trust dominate | **OpenAPI gives too much free credit** |
| cli_scorer | documentation (10-20 range) | Balanced |
| skill_scorer | documentation (14-25 range) | Slightly documentation-heavy |

---

## Recommended Priority Fixes

1. **P0**: Fix n8n connector scoring — either dedicated scorer or baseline adjustments in api_scorer
2. **P1**: Widen MCP score range — increase tool_quality baseline when tools metadata unavailable
3. **P1**: Reduce OpenAPI auto-credit in api_scorer OR raise Strong threshold for APIs
4. **P2**: Add `"homebrew": 2` to cli_scorer source_points
5. **P2**: Fix api_scorer `_score_documentation` to use actual `title` field
6. **P2**: Add penalty for non-active MCP registry status
7. **P3**: Reconsider skill_scorer scope_safety to be less popularity-dependent

## Can Each Scorer Run Without External API Calls?

**Yes** — all four scorers are pure functions operating on dict metadata only. No network calls, no file I/O, no database queries. They import only `re`, `datetime`, `typing`, and `urllib.parse`.
