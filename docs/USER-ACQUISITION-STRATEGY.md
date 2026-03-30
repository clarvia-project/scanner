# User Acquisition Strategy — Breaking Zero

**Author**: Clarvia CEO (Claude Opus)
**Date**: 2026-03-27
**Status**: Executable — Actions ordered by expected impact per effort
**Context**: 0 external users. Infrastructure ready. Product live. Need to break the dam.

---

## Diagnosis

### What we have
- 15,412 tools indexed, API live and healthy
- MCP server on npm (clarvia-mcp-server, 362 downloads, 4 versions)
- 16 tool types of MCP servers registered in catalog
- Sitemap with 15,413 URLs submitted to Google/Bing
- llms.txt, robots.txt with AI crawler permissions
- Agent identification middleware
- GitHub Action for CI/CD AEO checks
- Remote MCP endpoint at /mcp/

### What is broken
- **CRITICAL: GitHub repo is PRIVATE** — blocks MCP directory submissions, awesome-list PRs, GitHub Marketplace, framework integration PRs. Must go public FIRST.
- npm downloads are 0 for most days (362 total, likely CI mirrors)
- No Google Search Console verification = no indexing feedback
- MCP server not listed on mcp.so, Glama, or Smithery directories (only npm)
- GitHub Action not published to GitHub Marketplace
- API returns 404 on obvious paths (/api/v1/tools) = poor discoverability
- 0 Excellent-rated tools (scoring calibration issue)
- No Vercel Analytics = blind on actual traffic (FIXED: Analytics component added)

### Core insight
Agents do not browse the internet looking for tools. Agents use tools that humans configure for them. The acquisition funnel is:

```
Human developer encounters Clarvia
  -> Configures agent to use Clarvia MCP server
  -> Agent makes API calls
  -> Agent recommends Clarvia to other agents (via MCP tool responses)
  -> More humans hear about Clarvia from their agents
```

The bottleneck is step 1: **no human developer has encountered Clarvia in a context where they would configure it.** All marketing channels so far are passive (sitemap, npm listing, registry entries). We need active placement in the exact moments when developers are choosing tools.

---

## IMMEDIATE ACTIONS (Today ~ This Week)

### I1. Register on ALL MCP directories [Today]

**Why**: MCP directories are where developers go RIGHT NOW to find MCP servers. Clarvia is not listed on any of the top 3.

**Actions**:

1. **mcp.so** — Submit clarvia-mcp-server
   - Go to https://mcp.so/submit or use their GitHub-based submission
   - Repository: https://github.com/clarvia-project/scanner (mcp-server directory)
   - npm: clarvia-mcp-server

2. **Glama** — Submit to glama.ai MCP registry
   - They auto-index from npm if package has correct keywords
   - Verify: search "clarvia" on glama.ai. If not found, submit via their form
   - Our package.json already has correct MCP keywords

3. **Smithery** — Already have smithery.yaml in repo
   - Verify listing at smithery.ai
   - If not listed: `npx @smithery/cli publish` or submit via their dashboard

4. **mcp-registry (modelcontextprotocol/servers)** — Official Anthropic registry
   - Submit PR to https://github.com/modelcontextprotocol/servers
   - Add clarvia entry to the community servers list

5. **awesome-mcp-servers** — High-traffic GitHub list
   - Submit PR to https://github.com/punkpeye/awesome-mcp-servers
   - Category: "Tool Discovery" or "Developer Tools"

**Expected impact**: 50-200 views/week from directory browsers. 5-20 actual installations/week.
**Effort**: 2-3 hours total for all submissions.

### I2. Publish GitHub Action to GitHub Marketplace [Today]

**Why**: The GitHub Action already exists but is not on the Marketplace. The Marketplace is a high-trust discovery channel where developers actively look for CI/CD tools.

**Actions**:
- Verify action.yml has correct marketplace metadata (name, description, branding)
- Push to a public repo (or verify current repo is public)
- Go to GitHub Marketplace > Publish action
- Category: "Code Quality" or "Testing"
- Add clear README with usage example

**Expected impact**: 10-50 installations/month from Marketplace search.
**Effort**: 1 hour.

### I3. Add `.well-known/mcp.json` to clarvia.art [Today]

**Why**: This is the emerging standard for MCP server auto-discovery. Any agent or IDE that implements SEP-1649/SEP-1960 will find Clarvia automatically when visiting clarvia.art.

**Implementation**:
```json
// frontend/public/.well-known/mcp.json
{
  "name": "Clarvia",
  "description": "AI agent tool discovery and AEO scoring. Search 15,400+ tools, gate-check compatibility, find alternatives.",
  "url": "https://clarvia-api.onrender.com/mcp/",
  "transport": ["streamable-http"],
  "tools": 16,
  "homepage": "https://clarvia.art",
  "repository": "https://github.com/clarvia-project/scanner"
}
```

Also add `/.well-known/mcp/server-card.json` per SEP-1649.

**Expected impact**: Future-proofing. Small immediate impact, critical long-term.
**Effort**: 30 minutes.

### I4. Set up Vercel Analytics [Today]

**Why**: We are flying blind. Cannot measure any acquisition effort without analytics. Must be first action before any growth effort.

**Implementation**:
- `npm install @vercel/analytics` in frontend
- Add `<Analytics />` component to root layout
- Deploy to Vercel

**Expected impact**: No direct user acquisition, but enables measurement of everything else.
**Effort**: 15 minutes.

### I5. npm package v1.1.1 with improved description [Today]

**Why**: npm search is driven by package description, keywords, and README. Current version (1.1.0) is yesterday. Publish 1.1.1 with optimized metadata.

**Implementation**:
- Update package.json description to be more search-friendly
- Add "modelcontextprotocol" as first keyword (exact match for npm search)
- Ensure README has clear "Why use this?" section at top
- `npm publish`

Note: package.json already shows version 1.1.1, but npm shows 1.1.0 as latest. Need to actually publish.

**Expected impact**: 2-5x improvement in npm search discoverability.
**Effort**: 30 minutes.

---

## SHORT-TERM ACTIONS (1-2 Weeks)

### S1. Claude Desktop / Claude Code integration guides [Week 1]

**Why**: Claude users are the highest-intent audience. Claude Code supports `claude mcp add`. Claude Desktop supports mcp.json config. Creating integration content that appears when people search "claude mcp tools" or "best mcp servers for claude" captures purchase-intent traffic.

**Actions**:
1. Create `/guides/claude` page on clarvia.art
2. Include exact copy-paste config for Claude Desktop and Claude Code
3. Show real example: "Ask Claude to find the best database tool" -> Clarvia responds
4. Submit to Claude documentation community resources if such a page exists

**Expected impact**: 20-50 installations from Claude users specifically.
**Effort**: 4 hours.

### S2. Cursor / Windsurf / Cline integration guides [Week 1]

**Why**: Same logic as S1 but for IDE agent users. These three IDEs have MCP support and active communities.

**Actions**:
1. Create `/guides/cursor`, `/guides/windsurf`, `/guides/cline` pages
2. Each with exact config snippet
3. Optimize for SEO: "best mcp servers for cursor", "cursor mcp tools"

**Expected impact**: 30-100 views/week from search.
**Effort**: 3 hours (template-based).

### S3. "Top MCP Servers" curated pages [Week 1-2]

**Why**: This is the highest-value SEO play. Developers search for "best mcp server for X" constantly. No one owns these pages yet in Google. Clarvia has the data to generate authoritative ranking pages.

**Actions**:
1. Generate `/top/mcp-servers` main page (overall top 50)
2. Generate `/top/mcp-servers/database` (top database MCP servers)
3. Generate `/top/mcp-servers/developer-tools` (top dev tools)
4. Generate for each of the 26 categories
5. Each page: ranked list with score, brief description, install command
6. JSON-LD structured data for each (ItemList schema)

**Expected impact**: 200-1000 organic views/month within 4-8 weeks of indexing.
**Effort**: 8 hours (template + generation script).

### S4. MCP server npm README badges [Week 1]

**Why**: Tool authors want visibility. If Clarvia provides an embeddable badge (like shields.io), tool authors will put it in their READMEs. Every README view becomes a Clarvia impression.

**Actions**:
1. Badge endpoint already exists at backend (`/badge` routes)
2. Create a "Get your badge" page on clarvia.art
3. Generate badge URLs for top 100 MCP servers
4. Open PRs to 10-20 popular MCP server repos adding the Clarvia badge
   - Target repos with >50 stars that don't have quality badges yet
   - PR message: "Added AEO compatibility badge from Clarvia (free, no account needed)"

**Expected impact**: Each merged PR = 50-500 badge views/month. 10 merged PRs = 500-5000 monthly impressions.
**Effort**: 6 hours (badge page + 10 PRs).

### S5. PyPI package for Python developers [Week 2]

**Why**: The MCP server is Node.js only. Python is the dominant language for AI agent development. A Python SDK/CLI for Clarvia opens the PyPI discovery channel.

**Actions**:
1. Create `clarvia` Python package (thin wrapper around the REST API)
2. Core functions: `clarvia.search()`, `clarvia.score()`, `clarvia.gate_check()`
3. CLI mode: `clarvia search "database tools"`, `clarvia score https://example.com`
4. Publish to PyPI with proper classifiers and description
5. Keywords: "mcp", "ai-agent", "tool-discovery", "aeo"

**Expected impact**: Opens entire Python developer audience. 50-200 installs/month.
**Effort**: 8 hours.

### S6. Remote MCP endpoint promotion [Week 1]

**Why**: The remote endpoint (`https://clarvia-api.onrender.com/mcp/`) requires zero installation. This is the lowest-friction way to try Clarvia. But no one knows it exists.

**Actions**:
1. Add remote endpoint prominently to all README files
2. Register the remote endpoint specifically on MCP directories (some support remote servers)
3. Create a "Try without installing" section on the homepage

**Expected impact**: 2-3x conversion rate improvement for directory visitors.
**Effort**: 2 hours.

---

## MEDIUM-TERM ACTIONS (1 Month)

### M1. Agent framework integration PRs [Week 3-4]

**Why**: This is the highest-leverage action in the entire strategy. If one major agent framework embeds Clarvia data, every user of that framework becomes a potential Clarvia user.

**Targets** (in priority order):

1. **LangChain Hub** — Add Clarvia as a tool provider
   - PR: Add `ClarviaTool` to langchain-community
   - Allows any LangChain agent to search/evaluate tools via Clarvia

2. **CrewAI** — Add Clarvia tool
   - PR: Add Clarvia integration to crewai-tools
   - Use case: "Research agent that evaluates tool quality before recommending"

3. **AutoGen** — Add Clarvia skill
   - PR: Add tool evaluation capability via Clarvia API

4. **LlamaIndex** — Add Clarvia as a tool spec
   - PR: Add to llama-hub tool specs

**Implementation pattern** (same for all):
```python
from clarvia import ClarviaTool

# Agent can now search and evaluate tools
tool = ClarviaTool()
result = tool.search("best database connector for postgres")
# Returns scored, ranked results from Clarvia's 15,400+ tool catalog
```

**Expected impact**: If ONE PR merges, 1000-10000 potential users exposed monthly.
**Effort**: 12-16 hours total (3-4 hours per framework).

### M2. Tool author outreach program [Week 3-4]

**Why**: Tool authors who discover their Clarvia score become advocates. They share it, improve based on it, and put badges in their READMEs.

**Actions**:
1. Generate list of top 200 MCP server authors (from GitHub data we already have)
2. For each: current Clarvia score, top 3 improvement suggestions
3. Create GitHub Issues on their repos (not spam — genuine value):
   - Title: "Agent compatibility analysis for {tool-name}"
   - Body: Score breakdown, specific improvement suggestions, badge link
   - Only for repos with >20 stars (signals active maintenance)
4. Track which authors engage, claim their listing, improve their tools

**Expected impact**: 10-20% response rate = 20-40 engaged tool authors. Each becomes a long-term advocate.
**Effort**: 4 hours for script + 8 hours for 200 personalized issues.

### M3. Comparison pages for high-traffic tool pairs [Week 2-3]

**Why**: "[Tool A] vs [Tool B]" is a high-intent search. Developers searching this are actively making a tool selection decision. Clarvia can own these pages with data-driven comparisons.

**Top 10 comparison targets**:
1. Supabase MCP vs Prisma MCP
2. GitHub MCP vs GitLab MCP
3. Notion MCP vs Obsidian MCP
4. Postgres MCP vs MySQL MCP
5. Stripe MCP vs PayPal MCP
6. Slack MCP vs Discord MCP
7. AWS MCP vs GCP MCP
8. Docker MCP vs Kubernetes MCP
9. Puppeteer MCP vs Playwright MCP
10. OpenAI MCP vs Anthropic MCP

**Implementation**:
- Template: `/compare/{tool-a}-vs-{tool-b}`
- Auto-generated from existing score data
- Side-by-side dimension breakdown
- Recommendation based on use case
- JSON-LD ComparisonTable schema

**Expected impact**: 100-500 organic views/month per comparison page within 2 months.
**Effort**: 6 hours (template + generation).

### M4. Google Search Console setup + SEO audit [Week 2]

**Why**: Sitemap was pinged to Google, but without Search Console verification we have no idea if pages are being indexed. This is mandatory for any SEO strategy.

**Actions**:
1. Add clarvia.art to Google Search Console
2. Verify via DNS TXT record or HTML file
3. Submit sitemap.xml
4. Check indexing status for key pages
5. Fix any crawl errors
6. Set up Bing Webmaster Tools as well

**Expected impact**: Enables all SEO efforts. Without this, S3/M3 are blind shots.
**Effort**: 1 hour.

### M5. Weekly curated newsletter via API feed [Week 3-4]

**Why**: Not a human newsletter — a machine-readable feed that agents can subscribe to. New tools, score changes, trending categories. This gives agents a reason to check Clarvia regularly.

**Implementation**:
- `GET /v1/feed/weekly` — Returns this week's notable changes
- JSON format: new tools added, biggest score changes, trending categories
- Agents that integrate Clarvia MCP server can auto-check this feed
- Add `check_weekly_feed` tool to MCP server

**Expected impact**: Increases return usage for existing MCP server users.
**Effort**: 4 hours.

### M6. "AEO Score" branding push [Month 1]

**Why**: "AEO Score" needs to become a recognized term in the agent tool ecosystem. When developers see "AEO Score: 85" they should think Clarvia, just like "Lighthouse Score: 95" means Google.

**Actions**:
1. Consistent badge format: "AEO 85/100" with Clarvia branding
2. Encourage tool authors to include AEO score in their README
3. Add AEO score to every API response (already done)
4. Create `/aeo` explainer page — what is AEO, why it matters
5. Register aeo-score as npm keyword, PyPI classifier

**Expected impact**: Long-term brand recognition. No immediate traffic but compounds.
**Effort**: 4 hours.

---

## IMPACT PROJECTION

### Week 1 (Immediate actions I1-I5)
- MCP directory listings: +100-300 impressions/week
- npm search improvement: +20-50 views/week
- Analytics setup: measurement capability
- Total estimated new users: **5-15**

### Week 2-3 (Short-term S1-S6)
- Integration guides indexed: +50-200 views/week
- Top MCP server pages: +100-500 views/week (growing)
- Badge PRs merged: +500-2000 impressions/month
- PyPI package: +50-200 installs/month
- Total estimated new users: **20-50**

### Month 1 (Medium-term M1-M6)
- Framework integration PR: +1000-10000 potential users exposed
- Tool author outreach: +20-40 engaged authors
- Comparison pages: +500-2500 views/month
- Google indexing working: compound growth begins
- Total estimated new users: **50-200**

### Month 2-3 (Compound effects)
- SEO pages ranking: +2000-10000 views/month
- Tool author badges spreading: +5000-20000 impressions/month
- Framework integration users: +100-500 active API users
- Word of mouth from satisfied users
- Total estimated users: **200-1000**

---

## PRIORITY MATRIX

| Action | Impact | Effort | Do When |
|--------|--------|--------|---------|
| I4. Vercel Analytics | Enabling | 15 min | TODAY |
| I1. MCP directory listings | High | 2-3 hrs | TODAY |
| I3. .well-known/mcp.json | Medium | 30 min | TODAY |
| I5. npm v1.1.1 publish | Medium | 30 min | TODAY |
| I2. GitHub Marketplace | Medium | 1 hr | TODAY |
| M4. Google Search Console | Enabling | 1 hr | THIS WEEK |
| S3. Top MCP Server pages | High | 8 hrs | WEEK 1 |
| S6. Remote endpoint promo | Medium | 2 hrs | WEEK 1 |
| S1. Claude integration guide | High | 4 hrs | WEEK 1 |
| S4. Badge PRs to repos | High | 6 hrs | WEEK 1-2 |
| S5. PyPI package | High | 8 hrs | WEEK 2 |
| S2. IDE integration guides | Medium | 3 hrs | WEEK 2 |
| M1. Framework integration PRs | Very High | 16 hrs | WEEK 3-4 |
| M2. Tool author outreach | High | 12 hrs | WEEK 3-4 |
| M3. Comparison pages | High | 6 hrs | WEEK 2-3 |
| M5. Weekly feed endpoint | Medium | 4 hrs | WEEK 3-4 |
| M6. AEO branding | Long-term | 4 hrs | MONTH 1 |

---

## WHAT NOT TO DO

1. **No social media posts** — Agent-only marketing rule. No Twitter, Reddit, HN posts by humans.
2. **No paid ads** — Free route first rule.
3. **No email marketing** — We have no email list and no permission.
4. **No partnerships that require meetings** — We are a 1-person + AI team.
5. **No feature bloat** — The product works. The problem is distribution, not features.
6. **No premature monetization** — Zero users means zero revenue. Build trust first.

---

## SUCCESS CRITERIA

### Week 1 checkpoint
- [ ] Clarvia listed on mcp.so, Glama, Smithery
- [ ] Vercel Analytics live and reporting
- [ ] Google Search Console verified
- [ ] .well-known/mcp.json deployed
- [ ] npm v1.1.1 published
- [ ] At least 1 non-team visitor confirmed in analytics

### Month 1 checkpoint
- [ ] 50+ unique external visitors (confirmed via analytics)
- [ ] 10+ npm installs from non-CI sources
- [ ] 5+ tool profile pages indexed in Google
- [ ] 3+ badge PRs merged in external repos
- [ ] 1+ framework integration PR submitted
- [ ] 10+ tool authors aware of their Clarvia score

### Month 3 checkpoint
- [ ] 500+ unique monthly visitors
- [ ] 100+ npm installs/month
- [ ] 50+ Google-indexed pages
- [ ] 20+ tool authors engaged
- [ ] 1 framework integration live
- [ ] First organic mention of Clarvia by an external developer

---

## IMPLEMENTATION NOTES

### MCP directory submission details

**mcp.so submission**:
- URL: Check https://mcp.so for submit/add form
- Required: npm package name, GitHub repo URL, description
- Category: Developer Tools / Tool Discovery

**Glama submission**:
- URL: https://glama.ai/mcp/servers (check for submit option)
- They may auto-index from npm — search first
- If not indexed: use their submission form

**Smithery submission**:
- We have smithery.yaml in repo already
- Run `npx @smithery/cli deploy` or submit via https://smithery.ai
- Verify listing after submission

**awesome-mcp-servers PR**:
- Fork https://github.com/punkpeye/awesome-mcp-servers
- Add entry under appropriate category
- Format: `[Clarvia](https://github.com/clarvia-project/scanner/tree/main/mcp-server) - AI agent tool discovery and AEO scoring. Search 15,400+ tools, gate-check compatibility, find alternatives.`
- Submit PR with clear description

### .well-known/mcp.json implementation

Create file at `frontend/public/.well-known/mcp.json`:
```json
{
  "name": "Clarvia",
  "description": "AI agent tool discovery, scoring, and gate-checking. Search 15,400+ MCP servers, APIs, CLIs.",
  "url": "https://clarvia-api.onrender.com/mcp/",
  "transport": ["streamable-http"],
  "homepage": "https://clarvia.art",
  "repository": "https://github.com/clarvia-project/scanner",
  "tools_count": 16
}
```

Also create `frontend/public/.well-known/mcp/server-card.json` per SEP-1649.

### Vercel Analytics implementation

In frontend root layout:
```tsx
import { Analytics } from '@vercel/analytics/react';

// Add <Analytics /> inside the body
```

### Badge PR template for external repos

Title: `Add AEO compatibility badge`

Body:
```
This PR adds an AEO (Agent Engine Optimization) compatibility badge from [Clarvia](https://clarvia.art).

The badge shows how easily AI agents can discover and use this tool, scored on a 0-100 scale across 4 dimensions: API accessibility, data structuring, agent compatibility, and trust signals.

Current score: {score}/100 ({rating})

Badge is auto-updated and free. No account needed.

Preview: ![AEO Score](https://clarvia-api.onrender.com/v1/badge/{scan_id}.svg)
```

---

*This document is the primary acquisition playbook. Execute in order. Measure everything. Adjust weekly based on analytics data.*

*Next review: 2026-04-03 (1 week)*
*Owner: Clarvia CEO*
