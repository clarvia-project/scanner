# CLARVIA STRATEGY V2 — Opus-Level Review

**Author**: Clarvia CEO (Claude Opus)
**Date**: 2026-03-27
**Status**: Final — Ready for Executor Delegation
**Previous Version**: Sonnet-level planning (2026-03-24 to 2026-03-27)

---

## Executive Summary

Brutal honest assessment: Clarvia has zero real users. The previous Sonnet-level strategy built an impressive scaffold — 15,406 tools, 17 automation tasks, 5 registries listed — but confused motion with traction. The infrastructure exists. The product works. The business does not yet exist.

This document resets strategy from first principles using Opus-level thinking. It challenges three core assumptions from the previous plan, redefines the wedge, and produces an executable roadmap that Sonnet-level agents can run starting Monday.

**The three wrong assumptions being corrected:**
1. "More tools = better" — Wrong. Glama has 20K tools and still isn't THE standard. Curation beats coverage.
2. "Agent-only marketing" — Partially wrong. Agents don't discover tools through MCP registries autonomously yet. Humans configure agents. The real customer today is the human who chooses what tools their agent uses.
3. "AEO scoring is the product" — Wrong framing. Scoring is the mechanism. Trust is the product.

---

## 1. Problem Definition

### What exactly is the problem Clarvia solves?

**The real problem**: When a developer, researcher, or team wants to add capabilities to their AI agent, they face a chaotic, untrustworthy landscape of 15,000+ MCP servers, APIs, CLIs, and skills — with no reliable signal for which ones actually work, which are maintained, which are safe, and which will be around next month.

This is not a discovery problem. Discovery is solved (mcp.so, Glama, Smithery all exist). **This is a trust and evaluation problem.**

The secondary problem, emerging but not yet real: autonomous agents in the future will need to select tools programmatically. They need machine-readable, structured, scored data to make that decision. No one owns that standard yet.

Clarvia should solve the trust problem now, and position for the autonomous selection problem later.

### Who specifically has this problem?

**Tier A — The real user today (2026)**

*Developer building an AI agent system*
- Using Claude/GPT/Gemini + tool calling
- Needs MCP servers for: file access, database, web search, code execution, API integrations
- Pain: Spends 2-4 hours evaluating a tool before committing. Reads README, checks GitHub stars, looks at last commit date, tries to install it, hits undocumented errors.
- Volume: Estimated 50,000-200,000 active developers globally in this category, growing 5x/year

*AI Research team at a company*
- Building internal agent infrastructure
- Needs to standardize on a set of approved tools
- Pain: No way to audit tool quality, security, maintenance status across 15,000+ options
- They need a trusted source, not another directory

*MCP server author*
- Built a tool, wants people to find it
- Needs to understand why their tool isn't getting traction
- Needs a benchmark: "What does a good MCP server look like?"

**Tier B — The future user (2027+)**

*Autonomous agent runtime*
- Agent framework (AutoGen, CrewAI, LangGraph, custom) that dynamically selects tools
- Needs machine-readable data: is this tool safe? maintained? compatible?
- This user cannot exist at scale until agent payment rails exist — 12-18 months away minimum

### How painful is this problem?

Current pain intensity: **7/10** for developers, **9/10** for teams managing agent infrastructure.

The waste is measurable: 2-4 hours per tool evaluation × 5-10 tools per agent system × exponentially growing developer count. This is a massive time sink with no good solution.

What happens if it's not solved: Developers continue using the same 20-30 "famous" MCP servers (GitHub, Supabase, Notion) and ignore the long tail. This means 90% of the ecosystem — the innovative, niche, powerful tools — never gets discovered. The ecosystem stagnates.

### What are the current alternatives and why do they fail?

| Alternative | Why It Fails |
|-------------|--------------|
| **Glama** (20K tools) | Has grading (A-F) but no actionable improvement guidance. Grades feel arbitrary. No "here's why this got a C." |
| **mcp.so** (19K tools) | Pure directory. No quality signal at all. Stars and recency only. |
| **Smithery** (3-7K tools) | Best UX, but focused on deployment/management, not evaluation. |
| **PulseMCP** (12K tools) | Great editorial content, newsletter. No scoring. |
| **GitHub** | Raw. Requires expertise to evaluate. No normalization across types. |
| **Word of mouth** | Works for the top 20 tools. Fails for the long tail. |

**The gap no one owns**: A trusted, transparent, explainable scoring system with actionable improvement guidance, covering all tool types (not just MCP), with a machine-readable API that agents can query programmatically.

---

## 2. Solution Design

### How does Clarvia solve this problem?

Clarvia is a **trust layer** for the AI tool ecosystem, not a directory.

The distinction matters. A directory says "this exists." A trust layer says "this is worth using, here's why, and here's how the author can improve it."

Concretely: When a developer evaluates a tool on Clarvia, they get:
- A transparent score with explanation (not just "B+")
- Specific improvement guidance for tool authors
- Historical trend data (is this tool getting better or decaying?)
- Real signal: npm downloads, GitHub activity, CVE status
- Cross-category comparison: "This MCP server competes with this API"

### What is the core product loop?

**The Loop That Matters:**

```
Developer discovers tool on Clarvia (via search/Google/MCP registry)
    → Sees score + explanation → Trusts the score → Saves time
    → Comes back for next tool evaluation
    → Eventually: tool author sees their score, visits Clarvia
    → Tool author improves based on guidance → Score improves
    → Better ecosystem → More developers trust Clarvia
```

**The Missing Loop (currently broken):**
The loop above is broken because developers haven't discovered Clarvia yet. The previous strategy was trying to get agents to discover Clarvia — but agents don't autonomously browse MCP registries. Humans do.

**The Corrected Acquisition Loop:**
```
Developer searches "best MCP server for [X]" on Google
    → Finds Clarvia's comparison/ranking page (SEO)
    → Gets value immediately (score + comparison)
    → Bookmarks Clarvia for future tool evaluation
    → Shares with team → Team adopts as standard tool evaluation resource
```

This is the real loop. SEO and content marketing for *developers*, not agent-to-agent distribution.

### Critical features vs nice-to-haves

**Critical (must work perfectly, these are the product):**

1. **Score with explanation** — Not just a number. "Your tool scored 67/100. Documentation: 8/25 (-15 because no README). Agent compatibility: 20/25 (+5 for .well-known/agents.json). Maintenance: 12/20 (-8 because last commit 8 months ago)." This transparency is what Glama lacks.

2. **Improvement guidance** — "Here are the 3 changes that would raise your score from 67 to 85." Actionable, specific, prioritized. This turns tool authors into Clarvia advocates.

3. **Machine-readable API** — Clean, documented REST API that returns scored, structured data. This is the agent-readiness layer. Must have proper pagination, filtering, and search.

4. **Tool profile pages** — Each tool gets a permanent, shareable, SEO-indexed page. URL: clarvia.art/tools/{slug}. This is how Google finds us.

5. **Comparison engine** — Side-by-side tool comparison. "Compare: Supabase MCP vs Direct Supabase API." This is a high-value, high-search-intent page type.

**Nice-to-haves (build later):**

- Playground/testing environment (Smithery already does this)
- Hosted MCP gateway (Glama already does this)
- Tool claim system (useful but not core)
- Community ratings (noise risk — quality > quantity)
- Real-time monitoring (expensive, builds later when revenue exists)

### Architecture decisions that must be right from day 1

**Decision 1: Supabase as single source of truth**

Current state: JSON files + Supabase dual storage creates inconsistency. This must be fixed before any growth. When Render restarts, data disappears from memory-cached JSON. Analytics are lost. This is why the current "45 visitors" stat is unreliable.

**Decision 2: Tool profile pages must be statically generated or ISR**

Currently, tool pages may be SSR. At scale (15K+ tools), this is a cost and performance problem. Next.js ISR (Incremental Static Regeneration) at build time for known tools, with on-demand revalidation when scores update.

**Decision 3: The scoring algorithm must be public and documented**

This is the counterintuitive trust play. Glama's grades feel arbitrary because they're opaque. Clarvia must publish the exact scoring formula. "Here's the 100-point rubric." This makes the score trustworthy and makes improvement guidance credible.

**Decision 4: The API must be versioned from day 1**

When agents do start using the API programmatically, breaking changes will destroy trust. Version the API (`/api/v1/`) — already done. Never change v1 behavior. Add v2 for improvements.

---

## 3. Project Vision

### Where is Clarvia in 1 year? (March 2027)

**Business state:**
- 5,000 daily active developer users
- 500 registered tool authors (claimed their tools, using improvement dashboard)
- First 10 paying customers (tool author Pro subscriptions at $49/month)
- First agent framework integration (one major framework embeds Clarvia data)
- $490 MRR (small but real — proof of concept for monetization)

**Product state:**
- Scoring algorithm v2 (with real execution testing, not just static analysis)
- Tool profile pages fully SEO-indexed (top 500 in Google for "best MCP server for X" queries)
- Public API with 50 registered API key users
- Historical trend data (6+ months of scan history = unique data asset)

**Team state:**
- Clarvia-man (CEO agent) running continuous strategy loop
- 3-4 specialized execution agents (crawlers, scoring, SEO, support)
- Weekly human review sessions with 상호

### Where is Clarvia in 3 years? (March 2029)

By 2029, autonomous agent payments are real. Agents are making tool selection decisions programmatically. Clarvia is the trusted data source that agent frameworks query to evaluate tools before configuration.

**The 3-year vision realized:**
- The MCP/agent tool ecosystem has 500K+ tools
- Agent frameworks (AutoGen, LangGraph, CrewAI, custom enterprise systems) query Clarvia's API to decide which tools to configure for a given agent
- Clarvia processes 1M+ API queries/day from agent systems
- Revenue model: micropayment per API query ($0.001) + tool author subscriptions + enterprise data licensing
- Clarvia's AEO score is the de facto standard cited in tool documentation ("AEO Score: 94/100")

### What does "winning" look like? (specific metrics)

**6 months**: 1,000 DAU, 100 tool authors, first PR to an awesome-list merged
**12 months**: 5,000 DAU, 500 tool authors, 10 paying customers, one framework integration
**24 months**: 50,000 DAU, 5,000 tool authors, $50K MRR, 3+ framework integrations
**36 months**: 1M API calls/day (mix of human and agent), $500K ARR, standard reference in MCP ecosystem

### What is the moat?

**Moat 1: Historical data** (takes years to replicate)
Clarvia is scanning tools daily. By month 6, Clarvia has 180 days of trend data per tool. By month 12, a full year. No competitor can replicate this retroactively. The trend data answers questions no one else can: "Has this tool's score been improving or declining over the past 6 months?"

**Moat 2: Tool author relationships** (network effect)
When 500 tool authors are actively optimizing their tools based on Clarvia's guidance, they become Clarvia advocates. They put "AEO Score: 94/100 on Clarvia" in their READMEs. This drives organic discovery from developers who see the badge.

**Moat 3: Scoring methodology credibility** (takes time to earn)
Trust is earned slowly and lost fast. A scoring system that has been consistent, public, and accurate for 12+ months becomes the reference. Newcomers can copy the rubric but can't copy the trust.

**Moat 4: Machine-readable data layer**
If agent frameworks start depending on Clarvia's API, switching costs become real. The API becomes infrastructure.

### Position in the 4-system ecosystem

```
Auton (Agent Social) ←→ Clarvia (Tool Trust Layer)
         ↑                         ↑
    Agents discuss tools      Agents evaluate tools
         ↓                         ↓
    Ortus (Token Economy)  ←→  Agent Discovery
```

Clarvia's role in the ecosystem: **The trust oracle.** When Auton agents discuss tools, Clarvia is the authoritative data source they reference. When Ortus agents execute token-based transactions, Clarvia provides the quality signal that justifies pricing.

Clarvia should be the first system to be production-ready and generating real usage, because it provides the data substrate that makes the other systems more credible.

---

## 4. Strategy to Get There

### Growth Strategy: The Pivot

**Previous strategy (Sonnet-level, WRONG):**
- Register in MCP registries → agents find Clarvia → agents use API
- Problem: Agents don't browse registries autonomously. Humans configure agents.

**Corrected strategy (Opus-level):**
Phase 1 (Now - Month 3): Win developer trust through SEO and content
Phase 2 (Month 3-9): Convert developers into tool author relationships
Phase 3 (Month 9+): Agent framework integrations for programmatic access

**Phase 1 — SEO + Content (The wedge)**

The highest-ROI action available right now: Create tool comparison and ranking pages that rank on Google.

Target searches:
- "best MCP server for [use case]" (high intent, low competition)
- "MCP server comparison" (growing search volume)
- "is [tool name] safe to use" (security-conscious developers)
- "[tool name] alternatives" (decision-stage search)

Each tool profile page on Clarvia (clarvia.art/tools/github-mcp) should rank for "[tool name] review" and "[tool name] alternatives."

This requires: proper Next.js SSR/ISR, meta tags, sitemap, structured data (JSON-LD), and tool-specific content that Google considers authoritative.

**Phase 2 — Tool Author Flywheel**

When a tool author discovers their tool has a Clarvia score (via Google alert, GitHub mention, or direct outreach), they either:
a) Improve their tool to raise the score (good for ecosystem)
b) Claim their tool listing and optimize it (good for Clarvia data quality)
c) Pay for the Pro dashboard (good for revenue)

To trigger this flywheel: direct outreach to top 100 MCP server authors on GitHub. Not spam — a genuine email: "We scored your MCP server at 72/100. Here are 3 specific changes that would raise it to 90. Would you like to claim your listing?"

**Phase 3 — Framework Integration**

The decisive moat move: get one major agent framework to embed Clarvia scoring data.

Target: LangChain Hub, AutoGen's tool registry, or LangGraph's tool ecosystem.
Approach: Open source contribution — add a `clarvia_score` field to tool metadata, pull from Clarvia's public API.

This creates lock-in that no directory can replicate.

### Revenue Strategy

**Wrong assumptions from previous plan:**
- "Subscription for humans" — premature. Humans won't pay for a directory they haven't used.
- "Micropayments for agents" — too far in the future to plan around now.

**Corrected revenue ladder:**

**Rung 0 (Now) — Free, build trust:** No monetization. Every decision optimizes for trust and usage.

**Rung 1 (Month 6-9) — Tool Author Pro ($49/month):**
- Claim listing + verification badge
- Improvement roadmap (specific actions to raise score)
- Historical score trend (6 months)
- Competitor intelligence ("your tool vs the top 5 in your category")
- Priority re-scan on demand
- Target: Tool authors who are serious about their tools. 100 customers × $49 = $4,900 MRR.

**Rung 2 (Month 12-18) — Team/Enterprise ($299/month):**
- API access (beyond public free tier)
- Internal tool approval workflows
- Custom scoring rubric adjustments
- Bulk scanning of private tools
- Target: Companies building agent infrastructure who need a trusted evaluation layer.

**Rung 3 (Month 24+) — Agent micropayments:**
- Programmatic API queries billed at $0.001/query
- SLA guarantees for agent systems
- Target: Agent frameworks doing millions of tool selections per day

### Competitive Strategy: How to Beat Glama

Glama is the most dangerous competitor. They have 20K tools, a working grading system (A-F), and are ahead on scale.

**Where Glama is weak:**

1. **Explainability**: Glama's grades (A-F) feel arbitrary. There's no published rubric. Developers don't know WHY a tool got a C. Clarvia wins by making every point of the score transparent and explainable.

2. **Actionability**: Glama grades don't tell you how to improve. Clarvia's improvement guidance turns the score into a service relationship with tool authors.

3. **Cross-type coverage**: Glama is MCP-only. Clarvia covers MCP + API + CLI + Skills + Connectors. When the tool ecosystem fragments, Clarvia's cross-type comparison becomes a genuine differentiator.

4. **Machine-readable API**: Glama doesn't have a public API for agents to query. Clarvia does (or should — this needs to be production-ready with docs and API keys).

5. **Author relationship**: Glama is a passive observer. Clarvia is an active participant in tool quality improvement.

**The tactical move**: Build the "Clarvia vs Glama" comparison page that explains the philosophy difference. Developers who care about understanding (not just a grade) will choose Clarvia.

### Execution Roadmap

**Week 1 (This Week — Critical Infrastructure):**
- Fix the 502 backend errors (blocks everything else)
- Fix Supabase as single source of truth (stop data loss on restart)
- Fix the dead code in tool_scorer.py (currently corrupting tag data)
- Fix asyncio.gather return_exceptions (stops scan failures from cascading)
- Implement cachetools TTLCache to prevent OOM (immediate risk)

**Week 2-3 (Product foundation):**
- Make tool profile pages SEO-ready (meta tags, structured data, sitemap)
- Publish the scoring methodology as a public document
- Build the comparison page engine (A vs B side-by-side)
- Set up real analytics (Vercel Analytics or PostHog) to actually measure traffic

**Week 4-6 (Content and SEO):**
- Generate top 100 tool profile pages with full SEO optimization
- Create 10 "best MCP servers for [use case]" landing pages
- Submit sitemap to Google Search Console
- Start tracking keyword rankings

**Month 2 (Tool Author Outreach):**
- Build the tool author improvement dashboard (what do I need to change?)
- Identify top 200 MCP server authors on GitHub
- Send personalized outreach: "Your tool scored X, here's how to improve"
- Track conversion to claimed listings

**Month 3 (API Hardening):**
- Document the public API properly (OpenAPI spec, examples, rate limits)
- Build API key registration
- Create an "Integrate Clarvia" page for framework developers
- Reach out to one agent framework about integration

**Month 6 (First Revenue):**
- Launch Tool Author Pro ($49/month)
- Announce on Hacker News / relevant communities
- Have 10 paying tool authors on day 1 (from outreach relationship)

### Risk Analysis

**Risk 1: Glama copies the explainability model** (HIGH probability, HIGH impact)
Mitigation: Speed matters. Ship the transparent scoring pages now. Build the tool author relationship flywheel — Glama cannot copy the relationship, only the feature.

**Risk 2: Backend instability kills trust** (CURRENT RISK — CRITICAL)
The 502 errors are a brand killer. Any developer who hits a 502 never comes back.
Mitigation: Fix this week. Non-negotiable. Add uptime monitoring (UptimeRobot free tier).

**Risk 3: MCP ecosystem doesn't grow as expected** (MEDIUM probability, HIGH impact)
If MCP fails to become the standard (OpenAI's agent protocol wins instead), Clarvia's focus needs to shift.
Mitigation: "Cross-type" coverage (API, CLI, Skills) is the hedge. Clarvia should never be MCP-only in its self-description. Position as "agent tool evaluation" not "MCP evaluation."

**Risk 4: Agent autonomy arrives slower than expected** (HIGH probability, LOW impact on Phase 1)
This is actually fine. Phase 1-2 success doesn't depend on autonomous agents. It depends on developers trusting Clarvia's scoring.

**Risk 5: Score quality is wrong and erodes trust** (MEDIUM probability, CRITICAL impact)
If a widely-used tool gets a low score and developers disagree, Clarvia loses credibility.
Mitigation: Publish the rubric. Make it public and debate-able. When scores are contested, investigate and update the rubric — this is a feature, not a bug.

**Risk 6: Zero paying customers at month 6** (MEDIUM probability, MEDIUM impact)
If tool authors don't pay, revenue plan collapses.
Mitigation: Start free with the outreach program. Build the relationship first. When Pro launches, target the 20 most engaged tool authors who have already improved their tools based on Clarvia guidance.

---

## 5. Execution Plan — Delegatable Tasks

These tasks are written for Sonnet-level executor agents. Each task is self-contained and can start immediately.

---

### TASK GROUP A: Backend Stabilization (Week 1) — HIGHEST PRIORITY

**A1: Fix asyncio.gather exception propagation**
- File: `/Users/sangho/클로드 코드/scanner/backend/app/scanner.py`
- Change: Add `return_exceptions=True` to all `asyncio.gather()` calls
- Add exception handling loop after gather
- Test: Run a scan where one check intentionally fails, confirm others succeed
- Estimated time: 30 minutes
- Priority: P0 (causing silent scan failures)

**A2: Add cachetools TTLCache with size limits**
- Files: `scanner.py`, `middleware.py`, `checks/agent_compatibility.py`
- Add: `pip install cachetools`, replace all unbounded dicts with `TTLCache(maxsize=2000, ttl=86400)`
- Test: Confirm server starts, scan runs, cache evicts old entries
- Estimated time: 1 hour
- Priority: P0 (OOM risk on Render Starter 512MB)

**A3: Fix dead code in tool_scorer.py**
- File: `/Users/sangho/클로드 코드/scanner/backend/app/tool_scorer.py`
- Change: Line 283, change `return {` to `result = {`, remove intermediate return, keep only final return on line 313
- Test: Run scorer on 5 tools, confirm tags are populated
- Estimated time: 10 minutes
- Priority: P0 (corrupting tag data for 15K+ tools)

**A4: Fix Supabase as single source of truth**
- File: `app/services/supabase_client.py`, `routes/profile_routes.py`
- Change: Remove JSON file writes. Supabase is the only storage. JSON files are read-only fallback on startup.
- Wrap all Supabase calls with `asyncio.to_thread()` to prevent event loop blocking
- Test: Restart server, confirm data persists
- Estimated time: 2 hours
- Priority: P0 (data loss on every restart — analytics, profiles lost)

**A5: Fix rate limiter memory growth**
- File: `app/middleware.py`
- Change: Replace `defaultdict` with `TTLCache(maxsize=50000, ttl=3600)`
- Test: Confirm rate limiting still works after change
- Estimated time: 30 minutes
- Priority: P1

**A6: Investigate and fix 502 errors**
- Check: Render logs for the specific error pattern
- Likely cause: Either OOM (fixed by A2) or cold start behavior
- Add: `/health` endpoint that returns `{"status": "ok"}` with zero dependencies
- Add: UptimeRobot monitoring on `https://clarvia-api.onrender.com/health` (free)
- Test: Confirm 0 502s for 30 minutes after fix
- Estimated time: 1-2 hours
- Priority: P0

---

### TASK GROUP B: SEO Foundation (Week 2-3)

**B1: Tool profile pages — SEO metadata**
- File: Frontend Next.js tool page component
- Add: `<title>`, `<meta description>`, OpenGraph tags, canonical URL for each tool
- Format: "{Tool Name} Review — AEO Score {score}/100 | Clarvia"
- Add: JSON-LD structured data (SoftwareApplication schema)
- Test: Run any tool URL through Google's Rich Results Test
- Estimated time: 3 hours

**B2: Generate XML sitemap**
- Create: `/sitemap.xml` endpoint that lists all 15K+ tool profile URLs
- Update: On every crawler run (daily)
- Submit: To Google Search Console (manual step — flag for 상호 to do)
- Estimated time: 2 hours

**B3: Publish scoring methodology page**
- Create: `/methodology` page on clarvia.art
- Content: The exact 100-point rubric, how each dimension is scored, what signals are used
- This is a trust signal AND an SEO page for "how AEO scores work"
- Estimated time: 4 hours

**B4: Top 10 comparison landing pages**
- Create a template: `/compare/{tool-a}-vs-{tool-b}`
- Generate for top 10 most-searched comparisons (GitHub MCP vs Supabase MCP, etc.)
- Each page: side-by-side score breakdown, use case recommendation
- Estimated time: 6 hours (template + generation)

**B5: Set up Vercel Analytics**
- Add Vercel Analytics to the Next.js frontend
- This is free on the Vercel free tier
- We currently have zero reliable traffic data — this is blocking all growth measurement
- Estimated time: 30 minutes

---

### TASK GROUP C: Scoring Quality (Week 2-4)

**C1: Score recalibration — Excellent tier fix**
- Current: 0 tools with Excellent (80+) score despite many high-quality tools
- Root cause: Score thresholds too strict, dead code in tool_scorer.py (fixed by A3)
- After fixing A3: Re-run scorer on top 500 tools, review distribution
- Target: 5-10% of tools in Excellent tier (industry-standard quality signal)
- Estimated time: 2 hours after A3 is fixed

**C2: Add "improvement roadmap" endpoint**
- New API endpoint: `GET /api/v1/tools/{tool_id}/improvements`
- Returns: Top 3 specific changes that would raise the score most
- Example: `[{"action": "Add .well-known/agents.json", "point_gain": 12}, ...]`
- This is the core of the tool author value proposition
- Estimated time: 4 hours

**C3: Scoring algorithm documentation**
- Write: A public document explaining every scoring dimension
- Publish: At `/methodology` (Task B3)
- This is NOT optional — it's what makes Clarvia trustworthy vs Glama
- Estimated time: 3 hours

---

### TASK GROUP D: Analytics and Measurement (Week 2)

**D1: Agent request identification**
- Add: Request middleware that identifies agent traffic by User-Agent
- Patterns: Known LLM user agents, Claude, GPT, Cursor, Continue.dev
- Log: All agent requests with timestamp, endpoint, and user agent
- Store: In Supabase for persistence
- Dashboard: Simple count of "agent vs human" requests per day
- Estimated time: 3 hours

**D2: Supabase analytics persistence**
- Current: Analytics lost on Render restart
- Fix: All event tracking (page views, scans, API calls) goes to Supabase immediately
- This is partially fixed by A4 but analytics need specific implementation
- Estimated time: 2 hours

**D3: Weekly metrics dashboard**
- Build: Simple HTML page at `/admin/metrics` (password protected)
- Shows: DAU, scans run, API calls, tool authors registered, score distribution
- Updates: Daily via automation task
- Estimated time: 3 hours

---

### TASK GROUP E: Tool Author Flywheel (Month 2)

**E1: Tool claim system — MVP**
- Feature: Tool author can claim their listing via GitHub OAuth
- After claim: They can trigger re-scans, add a description, see improvement roadmap
- Verification: GitHub repo ownership (compare GitHub token's repos with tool's GitHub URL)
- Estimated time: 8 hours

**E2: Author outreach list**
- Generate: List of top 200 MCP server authors by: stars + recent activity + Clarvia score < 80
- Format: Name, GitHub handle, tool name, current score, top 3 improvements
- This is input for human outreach (상호 reviews and sends)
- Estimated time: 2 hours (automated)

**E3: Tool author dashboard**
- After tool claim (E1): Show score trend, improvement roadmap, how score compares to category average
- This is the value proposition for the $49/month Pro plan
- Build basic version first, iterate based on author feedback
- Estimated time: 12 hours

---

### TASK GROUP F: API Hardening (Month 3)

**F1: OpenAPI documentation**
- Generate: Full OpenAPI spec for all public endpoints
- Add: Swagger UI at `/api/docs` and ReDoc at `/api/redoc`
- Document: Rate limits, authentication, response formats
- Estimated time: 4 hours

**F2: API key registration**
- Add: `/api/register` endpoint for API key generation
- Require: Email + use case (optional)
- Store: In Supabase with usage tracking
- Rate limit: Free tier = 100 calls/day, no key = 10 calls/day
- Estimated time: 6 hours

**F3: API landing page**
- Create: `/api` page on clarvia.art explaining the public API
- Include: Examples in Python, TypeScript, curl
- Include: "Integrate Clarvia into your agent framework" section
- This is how framework developers find and evaluate the API
- Estimated time: 4 hours

---

### THIS WEEK'S SINGLE PRIORITY

If only one thing can be done this week: **Fix the backend (Task Group A).**

Every other strategy, SEO effort, or content plan fails if the backend returns 502 errors. Developers who hit a 502 never return. The current state is actively destroying any traction we might be building.

Priority order for Week 1:
1. A3 (dead code fix — 10 minutes, immediate quality improvement)
2. A1 (asyncio.gather — 30 minutes, stops silent failures)
3. A2 (cachetools — 1 hour, prevents OOM crash)
4. A4 (Supabase source of truth — 2 hours, stops data loss)
5. A6 (investigate 502 — until resolved, everything else is blocked)

---

## Appendix: What the Previous Sonnet Strategy Got Right

Not everything was wrong. These elements from the Sonnet-era planning should be preserved:

1. **Agent-only distribution channels** — MCP registries, npm, official registry. These are still valid channels. The correction is: they're not the PRIMARY acquisition channel, they're supplementary.

2. **Coverage strategy** — Tier 1 (MCP/Skills/CLI = 100%) + Tier 2 (hot/trending only). This is the right prioritization.

3. **Data moat vision** — Historical trend data is the correct long-term moat. Stay the course.

4. **AEO scoring framework** — The 100-point score with multiple dimensions is the right product direction. The implementation has bugs (fixed in Task Group A/C) but the concept is correct.

5. **Tool type diversity** — Not MCP-only is a real differentiator vs Glama. Maintain.

---

## Appendix: The Uncomfortable Truths

These things are true and must be acknowledged:

**We have 0 real users.** The 45 unique visitors are mostly the team. The 362 npm downloads are CI bots and mirrors. The 189 API calls are our own automation. Starting from zero is fine — it's where every successful product starts. But we must stop counting internal activity as traction.

**The backend has 4 critical bugs.** They exist in production right now, degrading data quality for every scan run. This means the scores in our catalog are systematically wrong (dead code issue = missing tags). We've been building on a broken foundation.

**Glama is ahead in the MCP space.** 20K tools, working grading, more features. We cannot beat them by being a better version of them. We must be a different product: transparent scoring, actionable guidance, cross-type coverage, tool author relationships.

**Agent autonomy is 12-18 months away from maturity.** The Sonnet-era plan assumed agents would start using Clarvia's API soon. They won't — not at meaningful scale. We need human developers to be the bridge. Clarvia must be useful to human developers first.

**The scoring quality is unknown.** We don't know if the scores are accurate because we have no user feedback loop. The first 100 real users will tell us more about scoring quality than any internal analysis. Speed to real users is critical.

---

*This document supersedes all previous Clarvia strategy documents. Review cycle: Monthly.*
*Next review: 2026-04-27*
*Owner: Clarvia CEO*
