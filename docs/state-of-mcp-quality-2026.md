# State of MCP Quality: Q1 2026 Analysis

> **Published**: March 2026 | **Last Updated**: April 1, 2026
> **Source**: Clarvia AEO Scanner — 27,886+ tools analyzed
> **Methodology**: AEO (Agent Engine Optimization) scoring across 5 dimensions

---

## Executive Summary

Clarvia has analyzed **27,886+ MCP servers and AI agent tools** indexed across major registries as of Q1 2026. The data reveals a stark quality gap: **only 0.3% of tools achieve Excellent AEO scores**, while **33% remain in the Weak tier** — meaning most AI agents fail to discover or effectively use the majority of available tools.

---

## Overall Quality Distribution

| Tier | Score Range | Count | % of Total |
|------|-------------|-------|------------|
| **Excellent** | 80-100 | 91 | 0.3% |
| **Strong** | 60-79 | 4,739 | 17.0% |
| **Moderate** | 40-59 | 13,827 | 49.6% |
| **Weak** | 0-39 | 9,195 | 33.0% |

**Average AEO Score**: 45.0/100

The majority of MCP tools (82.6%) score below 60, meaning they lack the machine-readable documentation, structured data, and discovery metadata that AI agents need to find and use them effectively.

---

## Category Performance

### Highest-Scoring Categories

| Category | Tools | Avg Score | Notes |
|----------|-------|-----------|-------|
| Cloud (AWS, GCP, Azure) | 1,084 | **66.6** | Best category — enterprise investment in docs |
| Collaboration | 33 | **64.2** | Small but well-documented |
| Analytics | 368 | **61.8** | Data-oriented devs prioritize schema |
| Telecom | 59 | **62.7** | High API standards requirement |
| Open Data | 292 | **54.1** | Strong specification culture |

### Lowest-Scoring Categories

| Category | Tools | Avg Score | Notes |
|----------|-------|-----------|-------|
| Storage | 33 | **33.7** | Missing agents.json, poor descriptions |
| Other/Uncategorized | 7,708 | **33.7** | Lack metadata for categorization |
| AI/ML Tools | 3,248 | **39.2** | Irony: AI tools least agent-discoverable |
| Design | 76 | **42.9** | Designer-focused, not machine-optimized |
| Education | 34 | **43.4** | Early stage, minimal documentation |

**Key Insight**: The "AI" category — tools built for AI workflows — has the *second-lowest* average AEO score (39.2), despite being the largest category with 3,248 tools. This suggests most AI tool developers optimize for human developers, not autonomous agents.

---

## The Discovery Gap

### Why 82% of MCP Tools Are Invisible to Agents

AEO scoring evaluates 5 dimensions:

1. **Machine Readability** — Does the tool expose `agents.json`, `llms.txt`, or OpenAPI?
2. **Tool Description Quality** — Are capabilities described in agent-parseable format?
3. **Schema Compliance** — Does `server.json` follow the MCP specification?
4. **Discovery Endpoints** — Are `.well-known/` endpoints present and valid?
5. **Structured Data** — Is Schema.org JSON-LD present for AI search engines?

The most common failures:
- **Missing `agents.json`**: 71% of tools have no agent discovery manifest
- **Poor tool descriptions**: 64% use human-oriented descriptions that don't match agent queries
- **No OpenAPI spec**: 58% of APIs lack machine-readable specifications
- **Missing structured data**: 89% lack Schema.org JSON-LD

---

## MCP-Specific Tools: The Meta Problem

The **MCP category** itself (1,258 tools explicitly classified as MCP servers) averages **49.4/100** — barely better than the overall average. This means the tools designed to extend AI agents are themselves poorly discoverable by AI agents.

### MCP Tool Quality Breakdown
- Total MCP-classified tools: 1,258
- Average AEO score: 49.4
- Excellent (80+): ~15 tools
- Strong (60-79): ~214 tools
- Moderate (40-59): ~625 tools
- Weak (0-39): ~404 tools

---

## Key Benchmarks: Developer Tools Category

With 9,630 tools, **Developer Tools** is the largest category (34.5% of all indexed tools). Average score: 49.8/100.

**What the best developer tool MCP servers have in common:**
1. Published OpenAPI 3.1 specification at `/openapi.json`
2. `agents.json` at `/.well-known/agents.json`
3. Tool descriptions >100 characters with use-case examples
4. Schema.org `SoftwareApplication` JSON-LD on their homepage
5. Active maintenance (updated within 30 days)

---

## Cloud vs. AI: The Quality Paradox

Cloud infrastructure tools (AWS, Cloudflare, GCP, Azure integrations) score **66.6/100** on average — the highest of any category. They have:

- Complete OpenAPI specifications
- Versioned APIs with changelogs
- Machine-readable authentication documentation
- Consistent endpoint naming patterns

Meanwhile, AI-specific tools score **39.2/100** — worse than blockchain (48.8) and ecommerce (52.1). The conclusion: enterprise cloud providers understand agent discoverability; most AI-native tool builders do not.

---

## Recommendations for MCP Server Developers

To move from **Moderate** (45 avg) to **Strong** (60+):

```bash
# Check your current AEO score
npx clarvia-mcp-server  # MCP server for Claude Code
# or
curl https://clarvia-api.onrender.com/v1/score?url=yourapi.com
```

**Quick wins (30-60 min each):**

1. **Add `agents.json`** to `/.well-known/agents.json`
   - Format: [JSON Agents Standard](https://clarvia.art/docs)
   - Impact: +8-12 points

2. **Improve tool descriptions** to 100+ characters with use cases
   - Before: `"Get user data"`
   - After: `"Retrieve complete user profile including name, email, permissions, and subscription status. Use when you need to verify user identity or check access rights."`
   - Impact: +5-10 points

3. **Publish `llms.txt`** at your root URL
   - Lists your capabilities for LLM context
   - Impact: +5-8 points

4. **Add Schema.org JSON-LD** to your main page
   - Type: `SoftwareApplication` with `applicationCategory: "DeveloperApplication"`
   - Impact: +10-15 points (AI search indexing)

---

## Trending: AEO Score Improvement Over Time

Based on Clarvia's weekly re-scanning of indexed tools, the average AEO score has improved:

- **March 2026**: 45.0/100 (current)
- **Estimated Q2 2026**: 47-50/100 (as major registries mandate quality)
- **Estimated Q3 2026**: 52-55/100 (as AEO becomes standard practice)

The improvement is driven primarily by major cloud providers and venture-backed startups improving documentation quality. The long tail (70%+ of tools) is expected to remain below 50 for at least 2 more quarters.

---

## Methodology

**Data Collection**: Clarvia indexes MCP servers from:
- Official MCP Registry (registry.modelcontextprotocol.io)
- Smithery.ai (2,500+ servers)
- npm registry (packages with `mcp-server` keyword)
- GitHub (repos with `mcp` topic)
- Community lists (punkpeye/awesome-mcp-servers, etc.)

**Scoring**: Each tool is analyzed across 5 dimensions using programmatic checks:
- HTTP endpoint probing
- Schema validation
- Content analysis
- Discovery endpoint verification
- Structured data extraction

**Freshness**: Tools are re-scanned weekly. Scores reflect capability at time of last scan.

**Limitations**: Score reflects technical discoverability, not functionality. A tool with an AEO score of 30 may work perfectly for human developers but be invisible to autonomous agents.

---

## Check Your Score

```bash
# Free AEO check via CLI
npx clarvia-mcp-server
# Then ask Claude: "Check the AEO score for my-api.com"

# Direct API
curl "https://clarvia-api.onrender.com/v1/score?url=your-mcp-server.com"

# Web interface
# https://clarvia.art/scan
```

---

*Data as of March 31, 2026. Clarvia re-scans all indexed tools weekly.*  
*Methodology: [clarvia.art/methodology](https://clarvia.art/methodology)*  
*Source code: [github.com/clarvia-project/scanner](https://github.com/clarvia-project/scanner)*
