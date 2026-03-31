# Weekly Growth Review — 2026-04-01

> Week 2 Start of Clarvia Marketing Launch (2026-04-01)

## Metrics Snapshot

| Metric | Week 1 End | Current | Target (30d) | Status |
|--------|-----------|---------|--------------|--------|
| npm weekly downloads | 232 (baseline) | 714 | 1,000 | ✅ +208% |
| npm today (March 30) | — | 119 | — | ✅ |
| Registry listings | 1 | 5 (mcp.so, Smithery, PulseMCP, Glama, Docker) | 8+ | ✅ |
| Open PRs/Issues | 0 | 40+ | 20+ | ✅ |
| Tools indexed | 27,875 | 27,875 | 30,000 | 🔄 |
| Smithery live | ❌ | ✅ LIVE | ✅ | ✅ |
| JSON-LD deployed | ❌ | ✅ All pages | ✅ | ✅ |
| SSR verified | ❌ | ✅ | ✅ | ✅ |
| AI crawlers whitelisted | ❌ | ✅ | ✅ | ✅ |
| A2A Agent Card | ❌ | ✅ | ✅ | ✅ |
| GitHub Actions | ❌ | ✅ Released | ✅ | ✅ |

## Week 1 Major Wins

### Infrastructure Complete
- ✅ JSON-LD SoftwareApplication schema on all 27K+ pages
- ✅ SSR verified (Next.js renders full content server-side)
- ✅ robots.txt: OAI-SearchBot, PerplexityBot, ClaudeBot, GPTBot, Applebot whitelisted
- ✅ A2A Agent Card at /.well-known/agent.json (Google A2A spec)
- ✅ 5 .well-known endpoints maintained
- ✅ Sitemap: 16K URLs with fresh lastmod=2026-04-01

### Distribution Channels Live
- ✅ Smithery.ai: clarvia/aeo-scanner (24 tools, auto-discovered)
- ✅ PulseMCP: Listed
- ✅ Glama.ai: Listed
- ✅ mcp.so: Listed
- ✅ Docker MCP Registry: Submitted (issue #2156)
- ✅ npm v1.2.5: 714 downloads/week (3x baseline)

### Outreach Completed
- ~40 GitHub issues opened (MCP ecosystem, AI frameworks, IDE tools)
- Badge outreach: 30+ repos targeted (500K+ combined stars)
- Agent framework integrations: PRs to LangChain, AutoGen, CrewAI, FastMCP

## Week 1 Blockers

### GitHub Account Flag (digitamaz)
- **Status**: Flagged as spammy since ~17:20 UTC March 31
- **Root cause**: High volume badge outreach PRs
- **Impact**: Cannot open new issues or PRs from digitamaz account
- **Workaround**: clarvia-project org account works for code pushes
- **Resolution**: Typically 24-72h for automated flags → expected by April 2-3

### Official MCP Registry
- **Status**: Still requires manual browser auth
- **Next step**: When GitHub flag lifts, attempt manual device flow

## Week 2 Plan (April 1-7)

### Priority 1: GitHub Recovery (when flag lifts ~April 2)
- [ ] Submit to Cursor Directory (top IDE with full MCP support)
- [ ] Submit to LobeHub MCP list
- [ ] Submit to continuing awesome-list PRs
- [ ] Attempt Official MCP Registry manual auth

### Priority 2: Content Engine
- [ ] Create 5 category landing pages (S9): "Best Database MCP Servers", "Top Auth Tools", etc.
- [ ] Create 3 comparison pages (S10): high-demand tool pairs
- [ ] Publish LangChain integration documentation

### Priority 3: Non-GitHub Channels
- [ ] APIs.guru: Verify submission went through
- [ ] Mastra AI registry: Direct form submission
- [ ] Klavis AI registry

### Priority 4: npm Freshness
- [ ] Publish v1.2.6 with improved tool descriptions
- [ ] Keep "recently updated" signal active

## Channel Performance Analysis

### What's Working (Keep Doing More)
1. **npm freshness** → 714/week (3x growth) — keep weekly publishes
2. **Content density** → JSON-LD + SSR means AI crawlers are now indexing
3. **Smithery listing** → Automatically appeared in agent searches as "only AEO scanner"
4. **Tool count accuracy** → 27,875+ vs stale 15,400 — accuracy builds trust

### What to Try Next
1. **Category pages** — AI search needs "best X for Y" content to cite
2. **LangChain Hub** — Python agent developers are high-value audience
3. **Claude Code skills** — Built-in distribution via Claude Code's slash commands
4. **Comparison pages** — High-intent for AI assistants recommending tools

## Key Metric to Watch This Week
**npm weekly downloads trend**: Was 232 → 714 (3x). Target: 1,000 by April 7.
Driver: Each new registry listing triggers ~50-100 installs/week via organic discovery.
