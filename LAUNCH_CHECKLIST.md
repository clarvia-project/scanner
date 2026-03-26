# Clarvia Launch Checklist

## Phase 0: Pre-Launch (Must Complete)

### Security
- [x] CORS whitelist (clarvia.art only)
- [x] SSRF protection (private IP blocking)
- [x] Webhook signature enforcement
- [x] Rate limit X-Forwarded-For hardening
- [ ] SSL verification in scanner (`ssl=True`)
- [ ] HSTS header (`Strict-Transport-Security`)
- [ ] Content-Security-Policy header
- [ ] X-Frame-Options, X-Content-Type-Options headers
- [ ] Stripe production keys configured
- [ ] Admin API key set (`SCANNER_ADMIN_API_KEY`)

### Product
- [x] Scan pipeline working (5 phases, 13+ sub-factors)
- [x] PDF report generation
- [x] Profile/badge system
- [x] Admin dashboard endpoints
- [x] Scoring precision improvement (8-tier)
- [ ] End-to-end payment flow tested (scan → checkout → webhook → PDF)
- [ ] Error messages sanitized (no stack traces in production)
- [ ] 404/500 pages customized

### Data
- [x] 44+ services scanned with real scores
- [ ] 150+ MCP services scanned (leaderboard)
- [ ] Score distribution validated (37-80 range, good spread)
- [ ] Prebuilt data served correctly on frontend

### Infrastructure
- [x] clarvia.art domain live
- [x] Vercel frontend deployed
- [x] Render backend deployed
- [x] CI/CD GitHub Actions
- [ ] Backend auto-restart on crash (Render handles this)
- [ ] Error monitoring (Sentry or similar)
- [ ] Uptime monitoring (UptimeRobot or similar)
- [ ] Database backup verified (Supabase)

---

## Phase 1: Soft Launch

### Go-to-Market
- [ ] Public leaderboard page with 150+ services
- [ ] "Scan Your Service" CTA on landing page
- [ ] Share on X/Twitter with top 10 scores
- [ ] Submit to Product Hunt
- [ ] Submit to Hacker News (Show HN)
- [ ] Contact top-scoring services ("You scored 80/100!")
- [ ] Contact low-scoring services ("Here's how to improve")

### Business
- [ ] Pricing page (Free scan / Pro $29/mo / Enterprise $299/mo)
- [ ] Stripe production checkout tested
- [ ] Terms of Service page
- [ ] Privacy Policy page
- [ ] Company email set up (e.g., hello@clarvia.art)

### Analytics
- [ ] PostHog or Mixpanel installed
- [ ] Key events tracked: scan_started, scan_completed, checkout_initiated, report_downloaded
- [ ] Conversion funnel: landing → scan → report → payment

---

## Phase 2: Growth

### Product
- [ ] MCP npm package published (@clarvia/mcp-server)
- [ ] Index API documentation (for agent developers)
- [ ] "Clarvia Certified" badge program (score >= 70)
- [ ] Historical score tracking (trend over time)
- [ ] Competitive benchmark reports
- [ ] Claude API integration for AI-powered recommendations

### Distribution
- [ ] MCP registry listings (smithery.ai, glama.ai, mcp.so)
- [ ] ElizaOS plugin
- [ ] Integration guides for popular agent frameworks
- [ ] Developer blog posts
- [ ] Newsletter launch

### Revenue
- [ ] Subscription billing (monthly recurring)
- [ ] x402 micropayments for Index API
- [ ] Enterprise custom reports
- [ ] "Clarvia Certified" annual re-certification fee

---

## Launch Decision Criteria

**Ready to launch when ALL Phase 0 items are checked.**

Current status:
- Phase 0: ~60% complete
- Blockers: Stripe keys, security headers, error monitoring, 150+ scans
- Estimated time to Phase 0 complete: 2-3 days
