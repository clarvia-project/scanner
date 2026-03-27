# Competitive Analysis: Tool Discovery Platforms
**Date**: 2026-03-27
**Purpose**: Identify features Clarvia should absorb from every major tool discovery platform

---

## CATEGORY 1: MCP/Agent Tool Directories (Direct Competition)

### 1. mcp.so
- **What it does**: Community-driven MCP marketplace; largest single-source MCP directory
- **Scale**: 19,051 MCP servers
- **Data collection**: User submissions + crawling GitHub
- **Unique features**: Hosted servers section, playground for testing, sponsored listings, feed/activity stream
- **UI/UX**: Card-based grid, featured/latest/official tabs, tag-based navigation, sidebar filtering
- **Business model**: Sponsorships (DeepSeek, ShipAny, CopyWeb), paid featured placements
- **Search/discovery**: Tags, categories, search bar, featured/latest sorting
- **Clarvia gap**: No playground, no feed/activity stream, no sponsored listings revenue model

### 2. Smithery (smithery.ai)
- **What it does**: MCP server registry + hosted deployment platform + CLI management tool
- **Scale**: 3,300-7,300+ servers (sources vary)
- **Data collection**: GitHub integration, user submissions, auto-discovery
- **Unique features**:
  - **One-click hosted deployment** (free hosting for side projects)
  - **CLI tool** for install/manage/develop MCP servers
  - **OAuth handling** built-in (generated OAuth modals)
  - **Runtime search** - agents can search Smithery at runtime via Toolbox
  - **Spec compliance** - keeps up with MCP spec changes automatically
- **UI/UX**: Clean directory with install instructions per client
- **Business model**: Free listings + free hosting; monetization unclear (likely enterprise tier)
- **Search/discovery**: Keyword + natural language search
- **Clarvia gap**: No hosting, no CLI, no runtime agent search API, no OAuth handling

### 3. Glama.ai
- **What it does**: MCP server registry with automated quality/security/license scoring
- **Scale**: 20,300 MCP servers (largest)
- **Data collection**: GitHub crawling + automated codebase scanning + user submissions
- **Unique features**:
  - **Triple-grade scoring system**: Security Grade (A-F), Quality Grade (A-F), License Grade (A-F)
  - **Automated security scans** of codebases
  - **Embeddable badges** showing grades
  - **30-day usage statistics** (tool invocation data)
  - **NPM download tracking**
  - **Environment filtering** (Remote/Local/Hybrid)
  - **Author claim/verification** system
  - **100+ categorical tags**
- **UI/UX**: Grid cards with grade badges, extensive sidebar facets, multiple sort options
- **Business model**: Free with possible premium tier (Stripe detected)
- **Search/discovery**: Deep search, relevance ranking, 6+ sort options, faceted filtering
- **Clarvia gap**: No automated security scanning, no letter grades, no embeddable badges, no environment type filtering

### 4. PulseMCP (pulsemcp.com)
- **What it does**: MCP directory + weekly newsletter + content hub
- **Scale**: 12,814 MCP servers
- **Data collection**: Crawling + community submissions
- **Unique features**:
  - **Weekly newsletter** (50+ editions, "THE MCP newsletter")
  - **Estimated weekly visitors** metric per server
  - **Trending section** highlighting popular servers
  - **Use cases section** showing real applications
  - **Classification system**: Anthropic References, Official Providers, Community
  - **Steering Committee credibility** (maintainer is MCP Steering Committee member)
- **UI/UX**: Clean card layout with trending sidebar, pagination
- **Business model**: Unclear (possibly sponsored newsletter)
- **Search/discovery**: Search bar, classification filters, 6 sort options, remote availability filter
- **Clarvia gap**: No newsletter, no estimated visitor metrics, no use case section, no editorial content

### 5. mcpservers.org
- **What it does**: Curated MCP server directory inspired by awesome-lists
- **Scale**: Hundreds (smaller, curated)
- **Data collection**: User submissions (free + premium)
- **Unique features**:
  - **Premium Submit** - one-time review fee for faster approval, official badges, dofollow links
  - **Status badges**: Official, Sponsor, Community
  - **Agent Skills** section (separate from servers)
  - **Remote Servers** dedicated section
- **UI/UX**: Simple card layout, category-based navigation
- **Business model**: Premium submissions (paid listings for priority review + badges)
- **Search/discovery**: Category browsing, name/newest sorting, search bar
- **Clarvia gap**: No premium submission tier, no differentiated badges for paid vs free

### 6. MCP Market (mcpmarket.com)
- **What it does**: MCP marketplace with leaderboard and skills directory
- **Scale**: 10,000+ tools and servers, 23 categories
- **Data collection**: GitHub crawling + community
- **Unique features**:
  - **GitHub Stars leaderboard** ranking servers by popularity
  - **Agent Skills directory** (separate from servers)
  - **Top 100 list** (curated ranking)
  - **Official servers** section highlighting major company implementations
- **UI/UX**: Clean marketplace layout
- **Business model**: Free directory
- **Search/discovery**: Category-based, leaderboard ranking
- **Clarvia gap**: No leaderboard, no Top 100 curated list

### 7. Composio (composio.dev / mcp.composio.dev)
- **What it does**: Integration platform with MCP support; connects AI agents to 500+ apps
- **Scale**: 850+ toolkits, 11,000+ tools
- **Data collection**: Built-in integrations (not a directory per se)
- **Unique features**:
  - **Unified authentication** across 500+ apps
  - **Direct API + MCP dual access** to same tools
  - **Pre-built tool actions** (not just discovery but execution)
  - **Sandbox execution environment**
- **UI/UX**: Developer-focused with code snippets
- **Business model**: Freemium (free tier + paid plans)
- **Clarvia gap**: No execution environment, no unified auth, no dual API/MCP access

### 8. Turbo MCP (turbomcp.ai, formerly mcp.run)
- **What it does**: Enterprise MCP gateway with security controls
- **Scale**: N/A (bring your own servers)
- **Data collection**: Self-hosted; no public directory
- **Unique features**:
  - **AI kill-switch** for immediate access deactivation
  - **RBAC for MCP servers**
  - **Audit logs** for compliance
  - **OIDC integration** for enterprise auth
  - **Data loss prevention** features
- **Business model**: Enterprise SaaS
- **Clarvia gap**: No enterprise governance features, no audit capabilities

---

## CATEGORY 2: General AI Tool Directories

### 9. There's An AI For That (theresanaiforthat.com)
- **What it does**: #1 general AI tool directory, comprehensive catalog
- **Scale**: Thousands of tools (exact count unstated, likely 10,000+)
- **Data collection**: User submissions + editorial curation
- **Unique features**:
  - **Task-based discovery** ("I need AI for X")
  - **Trending/Featured/Latest** multiple views
  - **Version history + changelog tracking** per tool
  - **Video demos and screenshots**
  - **Save/bookmark** functionality
  - **Pricing transparency** (free/freemium/trial displayed prominently)
  - **Deal-based sorting** (find tools with active deals)
- **UI/UX**: Dark theme, fixed nav, grid listings, sticky filters, mobile-responsive
- **Business model**: Sponsored/featured placements, possible affiliate
- **Search/discovery**: Multi-criteria filters, 5+ sort options, keyword search
- **Clarvia gap**: No task-based search ("I need a tool for X"), no version tracking, no video demos, no deal aggregation

### 10. Futurepedia (futurepedia.io)
- **What it does**: AI tool discovery + education platform
- **Scale**: 2,657 tools, 10 categories
- **Data collection**: Editorial curation + user favorites
- **Unique features**:
  - **Education integration** (14-Day AI Boot Camp, courses via Skill Leap)
  - **Favorites system** with counts (ChatGPT: 6,282 favorites)
  - **350,000+ user community**
  - **YouTube creator integration**
  - **Business function mapping** (Sales, Customer Service, Operations)
  - **Trust signals** (Harvard, Nvidia, Meta logos)
- **UI/UX**: Tab-based browsing, trending categories, recently added section
- **Business model**: Free directory + premium education (Skill Leap), advertising
- **Search/discovery**: Category browsing, favorites-based popularity, business function filter
- **Clarvia gap**: No education/learning content, no favorites count as popularity signal, no business function mapping

### 11. Toolify.ai
- **What it does**: Largest AI tool directory with traffic analytics
- **Scale**: 28,500+ tools, 450+ categories
- **Data collection**: Crawling + ChatGPT-assisted auto-updates
- **Unique features**:
  - **Traffic trends** per tool (actual web traffic data)
  - **"Most Saved" and "Most Used"** sections
  - **Auto-updated by ChatGPT** (AI-assisted curation)
  - **Multi-format tracking** (web, app, extension, GPT)
  - **450+ categories** (extremely granular)
- **UI/UX**: Standard directory layout with traffic sparklines
- **Business model**: Likely advertising + paid listings
- **Search/discovery**: Category-heavy, traffic-based popularity, multiple "top" lists
- **Clarvia gap**: No traffic analytics per tool, no AI-assisted auto-updates, no multi-format detection

### 12. TopAI.tools
- **What it does**: AI tool directory with comparison features and playbooks
- **Scale**: 20,536+ tools, 121 categories
- **Data collection**: Crawling + editorial
- **Unique features**:
  - **Side-by-side comparison** of multiple tools
  - **Expert-built playbooks** (curated workflows)
  - **Personalized recommendations**
  - **Smart search** with granular filters
  - **Curated rankings** by category
- **UI/UX**: Category cards, comparison tables
- **Business model**: Free to explore
- **Search/discovery**: Smart search, granular filters, personalized recommendations
- **Clarvia gap**: No side-by-side comparison tool, no playbooks/workflows, no personalized recommendations

### 13. AI Scout (aiscout.net)
- **What it does**: AI tool directory with built-in AI chatbot for discovery
- **Scale**: 1,800+ tools
- **Data collection**: Editorial curation
- **Unique features**:
  - **AI chatbot for discovery** - chat with it to find tools
  - **Custom AI solutions** - builds tools, not just lists them
  - **Daily updates**
- **UI/UX**: Standard directory + chatbot overlay
- **Business model**: Free directory + custom AI solutions services
- **Search/discovery**: AI chatbot-driven discovery, category browsing
- **Clarvia gap**: No AI chatbot for tool discovery, no custom solutions service

### 14. SaaS AI Tools (saasaitools.com)
- **What it does**: Curated generative AI tool directory
- **Scale**: 400+ tools, 13 categories
- **Data collection**: Editorial curation
- **Unique features**:
  - **Daily AI news** alongside directory
  - **Focus on generative AI** specifically
  - **100% free**
- **UI/UX**: Clean, category-based
- **Business model**: Free (unclear monetization)
- **Search/discovery**: Category browsing
- **Clarvia gap**: Minor; small scale, no unique features to absorb

---

## CATEGORY 3: Developer Tool Discovery

### 15. Product Hunt (producthunt.com)
- **What it does**: Daily product launch platform with community voting
- **Scale**: Thousands of daily launches, millions of users
- **Data collection**: Maker submissions + community votes
- **Unique features**:
  - **Daily leaderboard** with 24-hour competition window
  - **Upvote weighting system** (active users' votes count more)
  - **Anti-gaming mechanics** (shuffled rankings, hidden counts for 4 hours, vote weight decay for new accounts)
  - **Hunter/Maker identity system** (distinct roles)
  - **Kitty Points gamification** (weekly/monthly/yearly leaderboards for users)
  - **Launch event model** (not just listing, it's an EVENT)
  - **Comments as engagement** metric
  - **Weekly/monthly/yearly rankings** beyond daily
- **UI/UX**: Daily feed, leaderboard, comment threads, maker profiles
- **Business model**: Freemium (free launches + paid promoted placements + Ship subscription)
- **Search/discovery**: Daily curation, upvote-driven ranking, community discussion
- **Clarvia gap**: No launch event model, no gamification, no user reputation system, no daily competitive window, no anti-gaming mechanics

### 16. AlternativeTo (alternativeto.net)
- **What it does**: Crowdsourced software alternative finder
- **Scale**: Tens of thousands of apps
- **Data collection**: Crowdsourced user suggestions
- **Unique features**:
  - **"I want to replace X"** search paradigm (alternative-centric, not category-centric)
  - **Platform/license filtering** (Windows, macOS, Linux, iOS, Android + open source, free, paid)
  - **Thumbs up/down voting** on whether alternatives are good replacements
  - **Crowdsourced similarity scoring** (community votes on relevance)
- **UI/UX**: Tool-centric pages with alternative lists, platform badges
- **Business model**: Advertising + possibly paid listings
- **Search/discovery**: Alternative-based discovery, platform/license filters
- **Clarvia gap**: No "alternatives to X" feature, no platform/OS filtering, no replacement-specific voting

### 17. G2 (g2.com)
- **What it does**: Enterprise software review platform with quadrant scoring
- **Scale**: 100,000+ products, millions of reviews
- **Data collection**: Verified user reviews + market data
- **Unique features**:
  - **G2 Grid quadrant** (Leaders/High Performers/Contenders/Niche)
  - **Dual-axis scoring**: Satisfaction (50%) + Market Presence (50%)
  - **Review decay algorithm** (reviews lose weight over time: 90 days gradual, 18mo accelerated, 3yr plateau)
  - **Review quality scoring** (word count, Flesch Reading Ease)
  - **Verified reviews** (LinkedIn verification, email domain verification)
  - **Buyer intent data** (sold to vendors)
  - **Category comparison reports** (downloadable)
  - **15 market presence metrics** from multiple data sources
  - **Seasonal reports** (quarterly Grid updates)
- **UI/UX**: Grid visualization, detailed review cards, comparison tables
- **Business model**: Freemium reviews + enterprise buyer intent data + premium vendor profiles
- **Search/discovery**: Category grids, comparison, review-driven rankings
- **Clarvia gap**: No quadrant visualization, no review decay, no review quality scoring, no buyer intent data, no verified reviews, no market presence scoring

### 18. Capterra
- **What it does**: B2B software review directory (Gartner-owned)
- **Scale**: 100,000+ products, 900 categories, 2M+ reviews
- **Data collection**: Verified user reviews + vendor submissions
- **Unique features**:
  - **Custom scorecards** - buyers create their own evaluation criteria
  - **Vendor response** to reviews (two-way communication)
  - **Budget-based filtering** (filter by price range)
  - **Integration/feature matrices** per product
  - **Lead generation** for vendors
- **UI/UX**: Comparison tables, scorecard builder, review cards
- **Business model**: Pay-per-click (vendors bid on category + position), free listings with paid promotion
- **Search/discovery**: Category browsing, custom scorecards, budget filters
- **Clarvia gap**: No custom scorecard builder, no vendor response system, no PPC monetization model, no budget filtering

### 19. StackShare (stackshare.io)
- **What it does**: Tech stack discovery and company tech stack transparency
- **Scale**: 7,000+ technologies, 1.5M+ company profiles
- **Data collection**: User-generated stack declarations + Git repo analysis
- **Unique features**:
  - **Company tech stack profiles** ("What does Netflix use?")
  - **Stack comparison** (compare entire stacks, not just individual tools)
  - **Git repo integration** for auto-detecting stack
  - **"Stack decisions"** - engineers explain WHY they chose tools
  - **Enterprise version** for internal stack mapping
  - **Version tracking** and security vulnerability alerts
- **UI/UX**: Stack visualization, company profiles, decision threads
- **Business model**: Freemium + enterprise SaaS (Private StackShare)
- **Search/discovery**: Company-based discovery, stack-based browsing, decision-based learning
- **Clarvia gap**: No "who uses what" transparency, no stack decision rationale, no company profiles, no Git-based auto-detection

### 20. Awesome Lists (github.com/sindresorhus/awesome)
- **What it does**: Community-curated topic-specific tool lists on GitHub
- **Scale**: Millions of stars across thousands of lists
- **Data collection**: Community PRs + maintainer curation
- **Unique features**:
  - **Radical simplicity** - just Markdown files
  - **GitHub-native** (stars, PRs, issues as quality signals)
  - **Topic-specific depth** (e.g., awesome-mcp-servers)
  - **Track Awesome List** aggregator (trackawesomelist.com)
  - **CLI tools** for browsing (awesome-cli)
  - **Zero monetization** - pure community value
- **UI/UX**: Plain Markdown, GitHub-native
- **Business model**: None (open source)
- **Search/discovery**: GitHub search, community curation, stars as popularity
- **Clarvia gap**: No community PR-based submission model, no GitHub-native integration

---

## CATEGORY 4: API Directories

### 21. RapidAPI
- **What it does**: API marketplace with testing, management, and monetization
- **Scale**: 40,000+ APIs, 4.5M+ developers
- **Data collection**: API provider submissions + automated testing
- **Unique features**:
  - **In-browser API testing** (try before you integrate)
  - **Single API key** for all APIs (unified access)
  - **Performance metrics** (latency, uptime, popularity per API)
  - **Pricing tiers** per API (free/basic/pro/ultra)
  - **SDK generation** for quick integration
  - **Usage analytics** dashboard for consumers and providers
- **UI/UX**: API explorer, code snippet generator, pricing tables
- **Business model**: 20% commission on paid API subscriptions + enterprise tier
- **Search/discovery**: Category browsing, popularity ranking, performance metrics
- **Clarvia gap**: No in-browser testing, no unified access key, no performance metrics (latency/uptime), no commission-based monetization

### 22. APIs.guru
- **What it does**: Open-source API definition directory (OpenAPI specs)
- **Scale**: Thousands of API definitions
- **Data collection**: Community-driven + automated spec crawling
- **Unique features**:
  - **Machine-readable API definitions** (OpenAPI 2.0/3.x)
  - **REST API for the directory itself** (meta-API)
  - **RSS feeds** for added/updated APIs
  - **Metrics endpoint** (/metrics.json)
  - **Provider/service hierarchy** navigation
  - **100% open source**
- **UI/UX**: Minimal, developer-focused
- **Business model**: None (open source)
- **Search/discovery**: API endpoints for programmatic discovery, provider browsing
- **Clarvia gap**: No machine-readable tool definitions (API for our data), no RSS feeds, no programmatic access to directory

### 23. Public APIs (github.com/public-apis)
- **What it does**: Curated list of free public APIs
- **Scale**: 10,000+ APIs across 48 categories
- **Data collection**: Community PRs
- **Unique features**:
  - **Free JSON API** for accessing the directory programmatically
  - **Auth type labeling** (apiKey, OAuth, none)
  - **HTTPS/CORS support** indicators
  - **48 well-defined categories**
- **UI/UX**: GitHub Markdown table
- **Business model**: None (open source)
- **Search/discovery**: Category browsing, GitHub search
- **Clarvia gap**: No auth type labeling, no CORS/HTTPS compatibility indicators

---

## FEATURES TO ABSORB: Priority Ranking

### TIER 1: HIGH IMPACT, IMPLEMENT NOW

1. **Automated Quality/Security Scoring (from Glama)**
   - Letter grades A-F for Security, Quality, License
   - Automated codebase scanning
   - Embeddable badges for tool maintainers
   - *Why*: This IS Clarvia's core value prop. Glama does it well. Must match and exceed.

2. **"Alternative to X" Discovery (from AlternativeTo)**
   - "I want to replace X with something better" search paradigm
   - Show alternatives ranked by community votes
   - *Why*: Agents often need to SWITCH tools. This captures comparison intent directly.

3. **Quadrant/Grid Visualization (from G2)**
   - Plot tools on Satisfaction vs. Capability axes
   - Create Clarvia's own grid categories (Leaders, Rising Stars, Niche, Declining)
   - Review decay algorithm (older reviews lose weight)
   - *Why*: Visual positioning is extremely powerful for decision-making. G2 built a billion-dollar business on this.

4. **Traffic/Usage Analytics per Tool (from Toolify + PulseMCP)**
   - Show estimated weekly visitors/downloads per tool
   - Traffic trend sparklines
   - NPM/PyPI download counts
   - *Why*: Real usage data > self-reported claims. This is objective quality signal.

5. **API/Programmatic Access to Directory (from APIs.guru + Public APIs)**
   - REST API for Clarvia's data (so agents can query it)
   - Machine-readable tool definitions
   - RSS feeds for new/updated tools
   - *Why*: Agents ARE Clarvia's users. They need API access, not just a website.

### TIER 2: HIGH IMPACT, IMPLEMENT SOON

6. **Task-Based Discovery (from TAIFT)**
   - "I need a tool for [task]" search
   - Map tools to use cases, not just categories
   - *Why*: Users don't search by category. They search by problem.

7. **Side-by-Side Comparison (from TopAI.tools + Capterra)**
   - Compare 2-4 tools across all dimensions
   - Feature matrix comparison
   - Custom scorecard builder (let users weight what matters to them)
   - *Why*: Comparison is the #1 action before tool selection.

8. **Weekly Newsletter/Digest (from PulseMCP)**
   - Weekly digest of new, trending, and notable tools
   - Curated editorial content
   - Use case spotlights
   - *Why*: Builds recurring audience. PulseMCP's newsletter is THE channel for MCP community.

9. **Leaderboard/Rankings (from MCP Market + Product Hunt)**
   - GitHub stars leaderboard
   - Weekly/monthly most popular
   - Top 50 curated list (Clarvia's core product)
   - Rising tools (fastest growing)
   - *Why*: Leaderboards create engagement loops and competitive dynamics.

10. **In-Browser Testing/Playground (from mcp.so + RapidAPI)**
    - Try a tool before installing
    - Live demo/playground for MCP servers
    - *Why*: Reduces friction from discovery to adoption.

### TIER 3: MEDIUM IMPACT, STRATEGIC

11. **Launch Event Model (from Product Hunt)**
    - Daily/weekly "new tool spotlight" with community voting
    - Time-limited voting windows for fairness
    - Anti-gaming mechanics (weighted votes)
    - *Why*: Creates buzz and community engagement around new tools.

12. **User Reputation/Gamification (from Product Hunt)**
    - Reviewer reputation scores
    - Points for quality reviews/contributions
    - Leaderboard for top reviewers
    - *Why*: Incentivizes quality community contributions.

13. **"Who Uses What" Profiles (from StackShare)**
    - Show which notable agents/companies use which tools
    - "Stack decisions" - explain WHY a tool was chosen
    - *Why*: Social proof is the strongest purchase signal.

14. **Verified Reviews (from G2 + Capterra)**
    - Review verification (GitHub account, actual usage data)
    - Review quality scoring (detail, helpfulness)
    - Vendor/maintainer response to reviews
    - *Why*: Prevents fake reviews, builds trust.

15. **Environment/Platform Filtering (from Glama + AlternativeTo)**
    - Filter by: Remote/Local/Hybrid, OS, Language, License
    - Auth type labeling (API key, OAuth, none)
    - *Why*: Technical compatibility is a basic filtering need.

### TIER 4: NICE TO HAVE, DIFFERENTIATION

16. **AI Chatbot for Discovery (from AI Scout)**
    - Chat interface: "I need a tool that does X with Y integration"
    - Agent-to-agent: Clarvia as an MCP server that recommends tools
    - *Why*: Natural language discovery is the future. Clarvia should be both website AND tool.

17. **Education/Learning Content (from Futurepedia)**
    - How-to guides for top tools
    - Integration tutorials
    - Use case playbooks
    - *Why*: Turns discovery into adoption.

18. **Version/Changelog Tracking (from TAIFT + StackShare)**
    - Track tool updates and breaking changes
    - Alert users when tools they use get updated
    - *Why*: Post-adoption value keeps users coming back.

19. **Hosted Deployment (from Smithery)**
    - One-click deploy for MCP servers
    - Free hosting tier for community
    - *Why*: Removes the biggest friction point (installation).

20. **Runtime Agent Search API (from Smithery)**
    - Agents can search for tools at runtime via API
    - Dynamic tool discovery during task execution
    - *Why*: Enables autonomous tool selection by agents.

---

## KEY INSIGHTS

### What Nobody Does Well (Clarvia's Opportunity)
1. **Agent-first scoring**: All directories are human-first. None score tools specifically for agent consumption (reliability, error handling, response format quality).
2. **Cross-category coverage**: MCP directories only cover MCP. AI directories don't cover MCP. Nobody covers MCP + Skills + CLI + APIs in one place.
3. **Objective benchmarks**: Everyone uses stars/votes (vanity metrics). Nobody runs actual test suites against tools.
4. **Deprecation/health monitoring**: Nobody tracks when tools go unmaintained or start breaking.
5. **Integration compatibility mapping**: Nobody maps which tools work well TOGETHER.

### Competitive Positioning Summary
| Platform | Scale | Scoring | Testing | API | Newsletter | Comparison |
|----------|-------|---------|---------|-----|------------|------------|
| mcp.so | 19K | No | Playground | No | No | No |
| Smithery | 7K+ | No | Hosted | CLI | No | No |
| Glama | 20K | A-F grades | No | No | No | No |
| PulseMCP | 12K | No | No | No | Yes | No |
| TAIFT | 10K+ | Ratings | No | No | No | No |
| Toolify | 28K+ | Traffic | No | No | No | No |
| G2 | 100K+ | Grid quad | No | Yes | No | Yes |
| Capterra | 100K+ | Reviews | No | No | No | Scorecards |
| **Clarvia** | ? | Detailed scores | **Actual testing** | **Should build** | **Should build** | **Should build** |

### Clarvia's Unfair Advantage
- **Actually runs/tests tools** (nobody else does this)
- **Agent-native** (built for agent consumption, not just human browsing)
- **Cross-format coverage** (MCP + Skills + CLI + APIs in one place)
- **Quality scoring based on real data** (not just votes/stars)

### Top 5 Immediate Actions
1. Build Clarvia API (let agents query our data)
2. Add "Alternative to X" search feature
3. Create embeddable quality badges (like Glama's but better)
4. Launch weekly newsletter/digest
5. Build side-by-side comparison tool
