# Clarvia Re-Test Results (2026-03-25)

## Score Comparison

| Persona | Role | Before | After | Delta |
|---------|------|--------|-------|-------|
| Jake | MCP Server Operator (3 servers, 200+ DAU) | 5.0 | 7.0 | +2.0 |
| Sarah | API Developer (SaaS, 12-person team) | 6.5 | 8.5 | +2.0 |
| Marcus | AI Agent Builder (5 agents, 30+ APIs) | 6.0 | 8.0 | +2.0 |
| Diana | VP Engineering (Series B, 80 engineers) | 4.0 | 6.5 | +2.5 |
| Yuna | Indie Hacker (weather API, solo) | 6.5 | 7.5 | +1.0 |
| **Average** | | **5.6** | **7.5** | **+1.9** |

## What Was Resolved (per persona)

### Jake (5→7)
- MCP dedicated scan endpoint (/api/v1/mcp-scan)
- MCP weight 10→7 (honest rebalancing)
- New checks: idempotency, pagination, streaming
- Methodology transparency page

### Sarah (6.5→8.5)
- Scoring methodology fully public with rationale
- Hardcoded recs removed → all evidence-based
- Stack-specific code examples (Node/Python/Go)
- Scan history (localStorage delta)
- Blur paywall with clear free/paid boundary

### Marcus (6→8)
- Full API v1: /score, /leaderboard, /compare, /mcp-scan
- Rate limit 3→6, MCP 10→7 (aligned with reality)
- Leaderboard filters + compare + sort
- Authenticated scan endpoint

### Diana (4→6.5)
- API access (6 endpoints)
- Supabase persistence (not just in-memory)
- Privacy/security page
- Methodology transparency

### Yuna (6.5→7.5)
- Why AEO section with stats (3.2x, 67%, 4x)
- Case studies (3 services)
- Blur paywall (clear free/paid)
- Guide with stack selector + copy-paste code
- /api/v1/fix endpoint

## Remaining Gaps (for 7.5→9.0)

### 1. Account/API Key System (XL) — Diana dealbreaker
- User registration + login
- Per-user API keys (self-serve)
- Team workspaces with RBAC
- Mentioned by: Diana, Marcus

### 2. Server-Side Scan History (L)
- Persist scan history in Supabase
- GET /api/v1/history?url=... endpoint
- Team-shared history
- Mentioned by: Sarah, Diana

### 3. Stats Source Citations (S)
- 3.2x, 67%, 4x numbers need sources
- Add footnotes or "Based on analysis of X services"
- Mentioned by: Jake, Yuna

### 4. Monthly Pricing Model (M)
- Free tier: 3 scans/month
- Pro: $19-29/month unlimited scans + reports
- Team: $149/month with seats + API
- Mentioned by: Diana, Yuna

### 5. Agent Traffic Monitoring — Real Implementation (XL)
- Tracking middleware (detect agent user-agents)
- Dashboard: "3 agents called your API this week"
- Connects the causation loop
- Mentioned by: Yuna (game-changer), Marcus

### 6. Dynamic Verification (L)
- Actually call APIs (not just check headers exist)
- Test idempotency with real retry
- Verify pagination works across pages
- Mentioned by: Marcus, Jake

### 7. Score Reproducibility (M)
- Retry logic for external registry checks
- Cache external results (mcp.so, smithery)
- Confidence interval or variance indicator
- Mentioned by: Jake
