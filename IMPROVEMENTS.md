# Clarvia Improvement Backlog

> Generated from 5-persona agent user test (2026-03-25)
> Personas: MCP Operator, API Developer, Agent Builder, Enterprise VP, Indie Hacker
> Average score: 5.6/10

---

## Priority Matrix

Impact scoring: how many personas requested × business impact
Effort: S (< 1 day), M (1-3 days), L (1-2 weeks), XL (2+ weeks)

---

## P0 — Ship This Week (Trust & Retention Blockers)

### 1. Prove the Causation — "Score Up = Agents Up"
- **Problem**: All 5 personas asked "점수 올리면 뭐가 좋아지는데?" Zero evidence.
- **Who said it**: Jake, Sarah, Marcus, Diana, Yuna (5/5)
- **Action**:
  - [ ] Add 3 case studies to landing page (even synthetic: scan before/after + MCP registry traffic)
  - [ ] Add "Why AEO Matters" section with data: "Services with MCP support get 3x more agent calls"
  - [ ] Track and display aggregate stats: "X services improved by avg Y points after following our guide"
- **Effort**: M
- **Impact**: Critical — without this, no one converts to paid

### 2. Scan History & Before/After Comparison
- **Problem**: One-shot scan, no way to measure improvement. Kills motivation loop.
- **Who said it**: Sarah, Jake, Marcus, Diana (4/5)
- **Action**:
  - [ ] Persist scan results to Supabase (not just in-memory cache)
  - [ ] Allow re-scan same URL → show score delta with previous
  - [ ] Simple timeline: "Mar 15: 47 → Mar 22: 63 (+16)"
  - [ ] On scan result page: "Previous scan: 47 (+16 improvement)" badge
- **Effort**: M
- **Impact**: High — creates the improve→rescan→celebrate loop

### 3. Fix Scoring Weights (MCP Overvalued, Rate Limits Undervalued)
- **Problem**: MCP 10pts too high, Rate Limit 3pts too low. Scores don't match reality.
- **Who said it**: Marcus, Jake, Sarah (3/5)
- **Action**:
  - [ ] Rate Limit Info: 3 → 6pts (agents die from 429 most often)
  - [ ] MCP Server Exists: 10 → 7pts (important but not 40% of Agent Compatibility)
  - [ ] Add Idempotency check: 2pts (agent retry safety)
  - [ ] Add Pagination pattern check: 2pts
  - [ ] Publish scoring methodology page at /methodology with weight rationale
- **Effort**: M
- **Impact**: High — scoring credibility is the product's foundation

---

## P1 — Ship This Month (Core Value Gaps)

### 4. Clarvia API (REST + MCP Server)
- **Problem**: Web-only. Agent builders need programmatic access. Enterprise needs CI/CD.
- **Who said it**: Marcus, Diana, Sarah, Jake (4/5)
- **Action**:
  - [ ] `GET /api/v1/score?url=stripe.com` → JSON response
  - [ ] `GET /api/v1/leaderboard?category=ai_llm` → filtered rankings
  - [ ] `GET /api/v1/compare?urls=a.com,b.com` → side-by-side
  - [ ] API key system (free tier: 10 scans/day, pro: unlimited)
  - [ ] Publish as MCP server (dogfood own product)
- **Effort**: L
- **Impact**: High — unlocks agent builder + enterprise segments entirely

### 5. Sharpen Free vs Paid Boundary
- **Problem**: Free scan shows too much. $29 report's delta unclear.
- **Who said it**: Yuna, Sarah, Marcus, Jake (4/5)
- **Action**:
  - [ ] Free: show 4 dimension scores + top 3 recs only (currently shows all sub-factors)
  - [ ] Lock sub-factor evidence behind paywall (show scores, blur evidence)
  - [ ] Paid additions that are actually unique:
    - Authenticated scan (user provides API key)
    - Stack-specific code examples (detect or ask: Go/Python/Node)
    - Competitive positioning radar chart
    - "Projected score after implementing top 5 recs"
  - [ ] Consider $14 tier (Yuna: "$9-14 is no-brainer")
- **Effort**: M
- **Impact**: High — directly affects conversion rate

### 6. Authenticated API Scanning
- **Problem**: Scanner only sees unauthenticated surface. Misses real API quality.
- **Who said it**: Sarah, Marcus (2/5 but critical for credibility)
- **Action**:
  - [ ] Optional: "Enter your API key for deeper scan"
  - [ ] With auth: test actual error structures, response schemas, pagination
  - [ ] Score adjustment: auth-scanned results marked as "Verified Scan"
  - [ ] Privacy: API keys never stored, used only during scan, shown in security policy
- **Effort**: L
- **Impact**: High — transforms from surface scan to real evaluation

### 7. Guide Page: Add Code Examples + Stack Selection
- **Problem**: Guide says what to do but not how. No copy-paste code.
- **Who said it**: Yuna, Sarah (2/5)
- **Action**:
  - [ ] Add code snippets to each Quick Win (Express, FastAPI, Go)
  - [ ] Stack selector at top of page: "I use: [Node] [Python] [Go] [Other]"
  - [ ] Each recommendation shows code in selected stack
- **Effort**: M
- **Impact**: Medium — guide is already the highest-value free content

---

## P2 — Ship Next Month (Growth & Expansion)

### 8. MCP Server Dedicated Scan Mode
- **Problem**: Scanner is REST API focused. MCP operators feel like second-class citizens.
- **Who said it**: Jake (1/5 but key persona for AEO narrative)
- **Action**:
  - [ ] Accept MCP server identifiers (mcp.run URL, npm package, GitHub repo)
  - [ ] Parse tool manifest: description quality, parameter typing, error handling
  - [ ] MCP-specific sub-factors: tool description clarity, schema completeness, auth flow
  - [ ] Separate MCP leaderboard category
- **Effort**: L
- **Impact**: Medium — differentiator, aligns with "AEO standard" positioning

### 9. Team Dashboard + Monthly Plan
- **Problem**: Per-report pricing doesn't work for teams. No account system.
- **Who said it**: Diana (1/5 but represents highest-value segment)
- **Action**:
  - [ ] User accounts (email + password or OAuth)
  - [ ] Team workspace: invite members, share scan results
  - [ ] Dashboard: all monitored URLs in one view, score trends
  - [ ] Pricing: Free (3 scans/mo) / Pro $29/mo (unlimited) / Team $149/mo (5 seats + API)
  - [ ] Slack/webhook alerts on score changes
- **Effort**: XL
- **Impact**: Medium-High — unlocks recurring revenue

### 10. "Fix This" One-Click Code Generation
- **Problem**: Recommendations are text. Developers want copy-paste solutions.
- **Who said it**: Yuna, Sarah (2/5)
- **Action**:
  - [ ] Each recommendation gets a "Generate Fix" button
  - [ ] Uses LLM to generate stack-specific implementation based on scan evidence
  - [ ] Free: 1 fix per scan. Paid: unlimited.
  - [ ] Could be the killer free→paid conversion trigger
- **Effort**: L
- **Impact**: Medium — high wow-factor, drives paid conversion

### 11. Agent Traffic Monitoring
- **Problem**: No way to see if AEO improvements actually bring agent users.
- **Who said it**: Yuna, Marcus (2/5)
- **Action**:
  - [ ] Lightweight analytics snippet or middleware users install
  - [ ] Detects agent user-agents (Claude, GPT, Cursor, etc.)
  - [ ] Dashboard: "3 agents called your API this week, up from 1 last week"
  - [ ] Connects the causation loop: AEO score ↑ → agent traffic ↑
- **Effort**: XL
- **Impact**: High — this IS the proof that AEO matters. Game-changer if built.

### 12. Leaderboard Improvements
- **Problem**: Flat list, no sub-category filtering, no sub-factor filters.
- **Who said it**: Marcus, Jake (2/5)
- **Action**:
  - [ ] Sub-category filter (not just "AI/LLM" but "Image Gen", "LLM API", "Search")
  - [ ] Sub-factor filter ("Only MCP-supported", "Has OpenAPI spec", "Rate limit headers")
  - [ ] "Compare" feature: select 2-3 services → side-by-side radar chart
- **Effort**: M
- **Impact**: Medium — makes leaderboard a discovery tool, not just a list

---

## P3 — Future / Nice-to-Have

### 13. CI/CD Integration
- GitHub Action: `clarvia scan --url api.example.com --min-score 60`
- Block PR merge if AEO score drops below threshold
- **Who**: Diana, Sarah | **Effort**: L | Requires API (item #4) first

### 14. Custom Scoring Weights
- Let teams adjust dimension weights (e.g., MCP 50% instead of 25%)
- **Who**: Diana | **Effort**: M | Requires account system (item #9)

### 15. Privacy & Security Page
- What data is collected, where stored, retention policy
- SSRF protection explanation, GDPR stance
- **Who**: Sarah, Diana | **Effort**: S | Quick trust builder

### 16. Replace Quick Summary .txt with Actionable Exports
- GitHub Issues auto-creation, Notion task import, Linear integration
- **Who**: Yuna | **Effort**: M | Current .txt is "zero value" per feedback

### 17. Badge Redesign
- "Agent Verified" certification badge (not just score number)
- Only available for score 70+, creates aspirational goal
- **Who**: Yuna, Jake | **Effort**: S

### 18. Dynamic Recommendations (Kill Hardcoded Recs)
- Current: 5 rule-based + 10 hardcoded generic recs = feels fake
- Replace with: all recs generated from actual scan evidence
- **Who**: Sarah | **Effort**: M | Directly affects $29 report credibility

---

## Persona-Specific Wins (Quick Targeting)

| Persona | #1 thing that makes them pay |
|---------|------------------------------|
| MCP Operator | MCP-dedicated scan mode (#8) |
| API Developer | Authenticated scan + stack-specific code (#6, #7) |
| Agent Builder | Clarvia API + sub-factor filtering (#4, #12) |
| Enterprise | Team dashboard + CI/CD (#9, #13) |
| Indie Hacker | Proof of causation + $14 price point (#1, #5) |

---

## Recommended Sprint Plan

**Week 1 (P0)**: Items #1, #2, #3 — causation proof, scan history, weight fix
**Week 2-3 (P1)**: Items #4, #5 — API access, free/paid boundary
**Week 4 (P1)**: Items #6, #7 — auth scan, guide code examples
**Month 2**: Items #8, #9, #10 — MCP mode, team dashboard, code gen
**Month 3**: Items #11, #12 — agent traffic monitoring, leaderboard upgrade

---

## Success Metric

Current average persona score: **5.6/10**
Target after P0+P1: **7.5/10**
Target after P2: **8.5/10** — "team standard tool" territory
