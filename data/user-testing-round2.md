# Clarvia Platform — Round 2 User Testing Simulation

**Date:** 2026-03-26 (Post-improvement)
**Changes Applied:** 42 improvements across 6 files

## Changes Summary

| Area | Before | After |
|------|--------|-------|
| "other" category | 45% (6,944) | 5.0% (768) |
| Avg score | 38.4 | ~65 (estimated full rebuild) |
| Max score | 80 | 94+ |
| Score distribution | 70% weak | ~30% strong, ~45% moderate |
| Categories | 12 | 25 |
| MCP tools | 11 | 16 |
| API endpoints | 30+ | 40+ |
| New features | — | Collections, History, Rescan, Rank, Feedback view, Methodology, Keep-alive, Code snippets, Pricing field, Difficulty, Capabilities, similar_to, added_after |

---

## Re-test: Persona 1 — Alex (AI Agent Developer)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Top email MCP at 55 | Score recalibration (avg→65, MCP avg→71) | Top email MCP now scores 70-80. Meaningful differentiation. | ✅ 8/10 |
| 2 | Leaderboard meaningless | Recalibrated scores + rank field | Leaderboard shows rank #1-N with real score spread (50-94). | ✅ 8/10 |
| 3 | SendGrid scored low | Recalibrated + well-known org bonus | SendGrid as a well-known API now scores 70+. Trust restored. | ✅ 7/10 |
| 4 | Compare = just numbers | Dimensions now exposed with sub-factors in detail view | Compare still basic but dimensions show WHERE tools differ. | ⚠️ 6/10 |
| 5 | connection_info sparse | code_snippet field added for all typed services | Every MCP gets `npx -y pkg`, every CLI gets install command. | ✅ 8/10 |
| 6 | Recommend = search | Recommend endpoint + intent search unchanged | Still keyword-based but code_snippet + difficulty help. | ⚠️ 6/10 |
| 7 | Batch max 10 | Batch increased to 100 | 100 URLs in one call — sufficient for complex agents. | ✅ 9/10 |
| 8 | No uptime history | clarvia_probe unchanged + history endpoint | Still point-in-time, but history endpoint exists for future data. | ⚠️ 6/10 |
| 9 | Feedback = black hole | clarvia_submit_feedback + feedback view endpoint | Authors can see feedback now. Agents can read others' feedback. | ✅ 7/10 |
| 10 | Alternatives by category | similar_to parameter added | `?similar_to=scan_id` returns same-category tools, excluding original. | ✅ 8/10 |

**Alex Round 2: 7.3/10** (was 5/10, **+2.3**)

---

## Re-test: Persona 2 — Sarah (MCP Server Author)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Hard to distinguish from forks | Score spread (49→71 avg for MCP) | Her well-maintained tool now ranks distinctly higher. | ✅ 7/10 |
| 2 | No sub-factor breakdown | Dimensions with sub-factors in score_tool output | API returns 5 dimensions with max values. Clear improvement path. | ✅ 7/10 |
| 3 | Registration, no scan | Auto-scan + rescan endpoint | `POST /profiles/{id}/rescan` — no API key needed. | ✅ 8/10 |
| 4 | Badge score too low | Recalibrated scores | Badge now shows 70+ for decent MCP servers. Worth displaying. | ✅ 8/10 |
| 5 | No rank position | `/profiles/{id}/rank` endpoint | "Your tool ranks #47 of 464 in productivity" — exactly what she wanted. | ✅ 9/10 |
| 6 | No scoring docs | `/v1/methodology` endpoint | Full scoring methodology with dimensions, factors, thresholds, limitations. | ✅ 8/10 |
| 7 | No rescan API | `POST /profiles/{id}/rescan` | Open rescan with 1/hour rate limit. Can trigger after improvements. | ✅ 9/10 |
| 8 | Can't see feedback | `/profiles/{id}/feedback` endpoint | Aggregated feedback visible (total, success_rate, recent). | ✅ 7/10 |
| 9 | Compare basic | Dimensions in compare response | Side-by-side with 5 dimension scores. | ⚠️ 6/10 |
| 10 | No featured program | Still missing | Collections exist but no official "featured" curation. | ⚠️ 5/10 |

**Sarah Round 2: 7.4/10** (was 4/10, **+3.4**)

---

## Re-test: Persona 3 — Jin (Enterprise Architect)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Only 1% above 70 | Recalibrated (~30% strong) | ~4,500 tools score 70+. Meaningful pool to evaluate. | ✅ 7/10 |
| 2 | No compliance filters | Enhanced trust_signals (HTTPS, license, security keywords) | trust_signals now includes HTTPS, license, security keywords. Surface-level but present. | ⚠️ 5/10 |
| 3 | CSV export | Still works | ✅ Unchanged, still excellent. | ✅ 8/10 |
| 4 | Rate limit 100/min | Unchanged | Still 100/min. Enterprise tier not yet available. | ⚠️ 5/10 |
| 5 | No audit trail | Methodology endpoint + history endpoint | Methodology = scoring justification. History = trend tracking. Partial improvement. | ⚠️ 6/10 |
| 6 | Private scan results | Still public | Not fixed — needs separate work. | ❌ 3/10 |
| 7 | OpenAPI spec | Unchanged | ✅ Still good. | ✅ 8/10 |
| 8 | Webhooks | Score-change tracking via history | Webhooks exist. History snapshots enable change detection. | ✅ 7/10 |
| 9 | No team features | Still missing | Not addressed in this round. | ❌ 3/10 |
| 10 | No exportable report | Still missing | Collections can serve as "approved list" but no PDF export. | ⚠️ 4/10 |

**Jin Round 2: 5.6/10** (was 4.5/10, **+1.1**)

---

## Re-test: Persona 4 — Marcus (DevOps Engineer)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | CLI + SARIF | Unchanged | ✅ Still excellent. | ✅ 9/10 |
| 2 | No bulk scan from package.json | Still missing | Not addressed — good feature request for future. | ⚠️ 4/10 |
| 3 | No uptime history | History endpoint added | Point-in-time + daily snapshots. Better but not continuous. | ⚠️ 5/10 |
| 4 | No GitHub Action | Still missing | Not addressed in this round. | ⚠️ 4/10 |
| 5 | SARIF for PR checks | Unchanged | ✅ Still works. | ✅ 8/10 |
| 6 | Batch max 10 | Increased to 100 | 100 URLs per batch — handles enterprise-scale. | ✅ 9/10 |
| 7 | No score-change alerts | History snapshots enable detection | Can poll `/v1/history` to detect changes. Not push-based yet. | ⚠️ 6/10 |
| 8 | No self-hosted | Still missing | Enterprise requirement — not addressed. | ❌ 3/10 |
| 9 | Cold start 30s | Keep-alive ping every 14min | API stays warm. No more cold starts. | ✅ 8/10 |
| 10 | No Terraform provider | Still missing | Infrastructure as code — future work. | ⚠️ 4/10 |

**Marcus Round 2: 6.0/10** (was 5.5/10, **+0.5**)

---

## Re-test: Persona 5 — Luna (Startup Founder)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | AI category scores wrong | Recalibrated (OpenAI-type tools now 70+) | Top AI tools score 70-94. Meaningful ranking. | ✅ 7/10 |
| 2 | All MCP same score | Score spread (49→71 avg, 49-94 range) | Clear differentiation between MCP servers now. | ✅ 8/10 |
| 3 | No pricing data | Pricing field added ("free"/"freemium"/"paid"/"unknown") | Field exists but populated as "unknown" for most. Needs data enrichment. | ⚠️ 5/10 |
| 4 | No popularity signal | Popularity field added (0-100) | Field exists, defaults to 0. Needs real data pipeline. | ⚠️ 4/10 |
| 5 | Generic recommendations | Difficulty + code_snippet fields | Each tool has difficulty level and quick-start code. Helps choose. | ⚠️ 6/10 |
| 6 | Full scan detail | Unchanged | ✅ Still excellent. | ✅ 8/10 |
| 7 | No exportable report | Collections added | Can create curated collections and share. Not PDF but functional. | ⚠️ 6/10 |
| 8 | No trend data | History endpoint added | Daily snapshots. Can see ecosystem growth over time. | ⚠️ 6/10 |
| 9 | No free tier filter | Pricing field exists but mostly "unknown" | Structure ready, data needed. | ⚠️ 4/10 |
| 10 | No email digest | Still missing | Not addressed in this round. | ❌ 3/10 |

**Luna Round 2: 5.7/10** (was 3.5/10, **+2.2**)

---

## Re-test: Persona 6 — Dev (OSS Maintainer)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Tool found | Unchanged | ✅ Still auto-indexed from npm. | ✅ 7/10 |
| 2 | Score 48, no explanation | Recalibrated (now ~65-70) + methodology doc | Score is 65-70 now with clear dimension breakdown. Methodology explains why. | ✅ 7/10 |
| 3 | Badge embarrassing at 48 | Score now 65-70 | 70+ badge is worth displaying. Yellow/green color. | ✅ 7/10 |
| 4 | No claim/verification | Still missing | Not addressed — needs GitHub OAuth integration. | ❌ 3/10 |
| 5 | No usage stats | Feedback endpoint shows usage | Can see success_rate and latency from agent feedback. Early stage. | ⚠️ 5/10 |
| 6 | Can't see feedback | `/profiles/{id}/feedback` | Can see aggregated feedback. | ✅ 7/10 |
| 7 | No community channel | Still missing | Not addressed. | ⚠️ 4/10 |
| 8 | Probe too simple | Unchanged | Still basic HTTP check. | ⚠️ 4/10 |
| 9 | Competitive landscape | Better with score spread | Rankings more meaningful with recalibrated scores. | ✅ 7/10 |
| 10 | No spotlight | Collections could serve this | Community collections = user-generated spotlights. | ⚠️ 5/10 |

**Dev Round 2: 5.6/10** (was 3/10, **+2.6**)

---

## Re-test: Persona 7 — Priya (Security Engineer)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Trust signals shallow | Enhanced with HTTPS, license, security keywords | 3 new trust signals. Still surface-level but honest about limitations. | ⚠️ 4/10 |
| 2 | Auth type not quality | Unchanged | Still just type, not quality assessment. | ⚠️ 3/10 |
| 3 | No CVE data | Still missing | Explicitly documented in methodology as limitation. | ❌ 2/10 |
| 4 | No data flow analysis | Still missing | Not addressed. | ❌ 2/10 |
| 5 | No compliance report | Methodology doc exists | Methodology + limitations = transparency. Not a compliance report. | ⚠️ 4/10 |
| 6 | No allowlist/blocklist | Collections could serve this | Create a "Blocked Tools" collection as workaround. | ⚠️ 4/10 |
| 7 | No security alerts | History endpoint for change detection | Can detect score drops. Not security-specific alerts. | ⚠️ 4/10 |
| 8 | No provenance verification | Still missing | Needs blockchain/signing integration. | ❌ 2/10 |
| 9 | No rate limit info | Unchanged | Not addressed. | ⚠️ 3/10 |
| 10 | No pentest data | N/A | Expected — documented as limitation. | ❌ 2/10 |

**Priya Round 2: 3.0/10** (was 2/10, **+1.0**)

> Priya's feedback: "Honesty about limitations in the methodology doc is good. But the core issue remains — this isn't a security tool. At least stop calling it 'trust signals' and call it 'basic metadata checks'."

---

## Re-test: Persona 8 — Tom (Indie Hacker)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Quick answer for payments | Better scores for well-known tools | Top payments tools (Stripe etc) at 70+. Trustworthy recommendations. | ✅ 8/10 |
| 2 | No setup guide | code_snippet field | `npx -y pkg` or `curl api.example.com` ready to copy. | ✅ 7/10 |
| 3 | No code snippets | code_snippet added | Every typed service gets a quick-start snippet. | ✅ 7/10 |
| 4 | Categories don't match mental model | 25 categories (was 12) | New: database, cloud, security, testing, monitoring, automation, media, analytics. Much better. | ✅ 8/10 |
| 5 | Mobile responsive | Unchanged | Frontend not touched — unknown. | ⚠️ 5/10 |
| 6 | CLI scan works great | Unchanged | ✅ Still the best feature. | ✅ 9/10 |
| 7 | No favorites | Collections API | Can create personal collection of bookmarked tools. | ✅ 7/10 |
| 8 | Trending | Trending endpoint exists | Shows top tools, rising stars, category leaders. | ✅ 7/10 |
| 9 | No difficulty level | Difficulty field added | "easy"/"medium"/"hard" — helps estimate effort. | ✅ 7/10 |
| 10 | No free indicator | Pricing field (mostly "unknown") | Field exists but needs data. | ⚠️ 4/10 |

**Tom Round 2: 6.9/10** (was 5/10, **+1.9**)

---

## Re-test: Persona 9 — Yuki (Researcher)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Pagination fine | Unchanged + keep-alive (no cold start) | Faster data collection — no initial 30s wait. | ✅ 7/10 |
| 2 | Only 1 "strong" | Recalibrated (~4,500 strong) | Meaningful distribution: ~6% excellent, ~30% strong, ~45% moderate. | ✅ 8/10 |
| 3 | 45% "other" | Reduced to 5% with 25 categories | Taxonomy now has 25 categories. "other" at 5% is acceptable for research. | ✅ 8/10 |
| 4 | No time-series | History endpoint with daily snapshots | `/v1/history?days=30` — daily snapshots starting now. | ✅ 7/10 |
| 5 | No cross-reference IDs | scan_id still internal only | Still no DOI or npm/PyPI cross-reference. | ⚠️ 4/10 |
| 6 | No methodology doc | `/v1/methodology` endpoint | Full methodology: dimensions, factors, thresholds, limitations. Citable. | ✅ 8/10 |
| 7 | CSV export | Unchanged | ✅ Still works. | ✅ 8/10 |
| 8 | OpenAPI spec | Unchanged | ✅ Still excellent for programmatic access. | ✅ 8/10 |
| 9 | Score reproducibility | Methodology states "deterministic for same input" | Documented. Rescan available for verification. | ✅ 7/10 |
| 10 | No data license | CC-BY-4.0 in methodology | Explicit license + citation format provided. | ✅ 9/10 |

**Yuki Round 2: 7.4/10** (was 4/10, **+3.4**)

---

## Re-test: Persona 10 — Carlos (Product Manager)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | High-level overview | Stats + 25 categories | Much better ecosystem view with detailed category breakdown. | ✅ 7/10 |
| 2 | No popularity data | Popularity field (defaults 0) | Structure ready, data pipeline needed. | ⚠️ 4/10 |
| 3 | No competitive analysis | similar_to parameter | Can find alternatives to any tool. Useful for competitive landscape. | ⚠️ 6/10 |
| 4 | No build vs buy | Difficulty + agent_compatibility dims | Difficulty + compatibility score hints at "use existing" vs "build custom". | ⚠️ 5/10 |
| 5 | No effort estimation | Difficulty field | "easy"/"medium"/"hard" — basic but helpful. | ⚠️ 5/10 |
| 6 | No demand signals | Still missing | Not addressed. | ❌ 3/10 |
| 7 | No stakeholder report | Collections + methodology | Can create collection + share methodology as justification. Not PDF. | ⚠️ 5/10 |
| 8 | No category growth | History endpoint | Daily snapshots include by_category counts. Can track growth. | ✅ 7/10 |
| 9 | Cold start/reliability | Keep-alive eliminates cold starts | API now always warm. Reliable for product dependency. | ✅ 8/10 |
| 10 | No pricing page | Still missing | Not addressed for Clarvia's own pricing. | ⚠️ 4/10 |

**Carlos Round 2: 5.4/10** (was 3/10, **+2.4**)

---

## Re-test: Persona 11 — Ava (Autonomous Agent)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Keyword search | Intent search + better descriptions | Combined with recalibrated scores, search results are more relevant. | ⚠️ 7/10 |
| 2 | gate_check pass/fail | Unchanged (still great) | ✅ Fast binary decision. Scores more meaningful now. | ✅ 9/10 |
| 3 | Category-level alternatives | similar_to parameter | `?similar_to=scan_id` — exactly what she wanted. | ✅ 9/10 |
| 4 | connection_info + code_snippet | code_snippet for all typed services | Auto-configure from code_snippet + connection_info. | ✅ 9/10 |
| 5 | Feedback submission | clarvia_submit_feedback + get_feedback | Full feedback loop: submit and read. | ✅ 8/10 |
| 6 | Verbose discovery | Trending MCP tool + 25 categories | `clarvia_trending` for quick discovery. Much more targeted. | ✅ 8/10 |
| 7 | clarvia_probe | Unchanged | ✅ Quick availability check. | ✅ 8/10 |
| 8 | No machine-readable capabilities | Capabilities field added | Field exists (array), populated programmatically. | ⚠️ 6/10 |
| 9 | No cost data | Pricing field (mostly "unknown") | Field exists but needs enrichment. | ⚠️ 4/10 |
| 10 | No workflow chains | Still missing | Needs separate recommendation engine. | ⚠️ 4/10 |

**Ava Round 2: 7.2/10** (was 6/10, **+1.2**)

---

## Re-test: Persona 12 — Ray (Curator)

| UC# | Issue | Fix Applied | New Experience | Score |
|-----|-------|------------|----------------|-------|
| 1 | Browse top per category | Better scores + 25 categories | 25 categories with real score spread. Excellent for curation. | ✅ 8/10 |
| 2 | No collections | Collections CRUD API | Full create/read/update/delete for curated lists. | ✅ 8/10 |
| 3 | No editorial notes | Collection description field | Can add description to collection. Not per-tool notes yet. | ⚠️ 6/10 |
| 4 | No embeddable widgets | Badge only | Still just badge. No embeddable comparison tables. | ⚠️ 4/10 |
| 5 | No "newly added" | added_after date filter | `?added_after=2026-03-20` — exactly what he wanted. | ✅ 8/10 |
| 6 | No community ratings | Still missing | Not addressed. | ⚠️ 4/10 |
| 7 | No shareable URLs | Collection GET returns full data | `/v1/collections/{id}` is shareable. | ✅ 7/10 |
| 8 | API for content generation | Improved API with more data | More fields = better auto-generated content. | ✅ 8/10 |
| 9 | No ranking changes | History endpoint | Can detect biggest movers via daily snapshots. | ✅ 7/10 |
| 10 | No affiliate program | Still missing | Business model decision, not addressed. | ⚠️ 3/10 |

**Ray Round 2: 6.3/10** (was 3.5/10, **+2.8**)

---

## Final Comparison

| Persona | Round 1 | Round 2 | Delta | Key Improvement |
|---------|---------|---------|-------|----------------|
| Alex (Agent Dev) | 5.0 | **7.3** | +2.3 | Score trust, batch 100, similar_to |
| Sarah (Tool Author) | 4.0 | **7.4** | +3.4 | Rescan, rank, feedback, methodology |
| Jin (Enterprise) | 4.5 | **5.6** | +1.1 | Better scores, keep-alive |
| Marcus (DevOps) | 5.5 | **6.0** | +0.5 | Batch 100, keep-alive |
| Luna (Founder) | 3.5 | **5.7** | +2.2 | Score recalibration, collections |
| Dev (OSS) | 3.0 | **5.6** | +2.6 | Score boost, feedback view, rank |
| Priya (Security) | 2.0 | **3.0** | +1.0 | Methodology transparency |
| Tom (Indie) | 5.0 | **6.9** | +1.9 | Code snippets, difficulty, categories |
| Yuki (Researcher) | 4.0 | **7.4** | +3.4 | Methodology, license, 25 categories |
| Carlos (PM) | 3.0 | **5.4** | +2.4 | History, categories, keep-alive |
| Ava (Agent) | 6.0 | **7.2** | +1.2 | similar_to, trending, feedback loop |
| Ray (Curator) | 3.5 | **6.3** | +2.8 | Collections, date filter, history |

### Overall Average: 4.1/10 → **6.2/10** (+2.1)

### Score Distribution
- Round 1: 0 personas above 7/10
- Round 2: **4 personas at 7+ /10** (Alex, Sarah, Yuki, Ava)

### Remaining Gaps (for Round 3)
1. **Enterprise features** (Jin: 5.6) — Private scans, team accounts, SLA, compliance
2. **Security depth** (Priya: 3.0) — CVE integration, compliance frameworks, data flow
3. **Data enrichment** (Luna: 5.7) — Pricing, popularity, usage counts need real data pipelines
4. **Developer experience** (Marcus: 6.0) — GitHub Action, package.json audit, Terraform
5. **Demand intelligence** (Carlos: 5.4) — Search analytics, agent usage tracking, trend reports
