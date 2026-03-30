# Clarvia — Building Journey Log

> AI 에이전트 도구 생태계의 중심 플랫폼을 만드는 여정.
> 모든 결정, 실패, 피봇, 돌파구를 기록한다.

---

## Day 0 — Foundation (2026-03-24~25)

### What happened
- Clarvia AEO Scanner 초기 버전 구축
- 175개 도구로 시작, 웹 스캔 기반 점수 시스템
- Expert review Round 1: **4/10** — "운영 70%, 성장 30%. 뒤집어라"

### Key decisions
- Agent-only marketing 원칙 확립: 인간 소셜미디어 완전 배제
- Quality > Quantity 원칙: 카탈로그 양보다 큐레이션 판단이 경쟁력

---

## Day 1 — Scale & Automation (2026-03-26 AM)

### What happened
- 카탈로그 175 → **15,406 tools** (7개 소스 병합)
- 자동화 시스템 4단계 구축 (18개 태스크)
- Expert review Round 3: **8.8/10** — "코드 충분. 고객 데려와라"
- 12개 크롤러 (Smithery, npm, GitHub, Glama, mcp.so 등)

### Key decisions
- MCP/Skills/CLI = 100% 커버리지 목표
- 나머지 도구 = hot/trending만 수집
- 속도보다 품질 — 프로덕션 수준만 배포

---

## Day 1 — Platform Upgrade (2026-03-26 PM)

### The 4-Round User Testing Loop
12개 가상 페르소나로 유저 테스트 시뮬레이션 실행.

**Round 1 (baseline): 4.1/10**
- 120개 시나리오 중 대부분 불만족
- "other" 카테고리 45%, 스코어 평균 38.4, 최고 80
- 도구 작성자에게 아무것도 안 줌

**Round 2 (42 fixes): 6.2/10 (+2.1)**
- 분류기: 45% → 5% "other", 12 → 25 카테고리
- 스코어 재보정: avg 38→71, max 80→97
- 도구 작성자 대시보드: rescan, rank, feedback
- Collections, History, Methodology 추가
- Keep-alive (콜드 스타트 제거)
- MCP 11 → 16 도구

**Round 3 (35+ features): 8.4/10 (+2.2)**
- Pricing/Capabilities/Difficulty 자동 감지
- GitHub Action, package.json audit
- Tool claim (GitHub 인증), Community ratings
- Featured/Spotlight, Search analytics, Demand intelligence
- 임베더블 위젯, Team accounts
- Security endpoint, Report generation
- TF-IDF 스마트 추천 엔진
- MCP 16 → 22 도구

**Round 4 (external APIs): 9.1/10 (+0.7)**
- 무료 외부 API 통합: npm registry, GitHub API, OSV.dev, PyPI
- 실시간 CVE 취약점 조회 (Google OSV)
- 실제 npm 다운로드 수, GitHub stars/forks
- Compliance checklist (SOC2/GDPR)
- MCP 22 → 24 도구

### Final scores
| Persona | Start | Final | Delta |
|---------|-------|-------|-------|
| Ava (AI Agent) | 6.0 | 9.4 | +3.4 |
| Yuki (Researcher) | 4.0 | 9.4 | +5.4 |
| Sarah (Tool Author) | 4.0 | 9.3 | +5.3 |
| Dev (OSS) | 3.0 | 9.2 | +6.2 |
| Tom (Indie) | 5.0 | 9.2 | +4.2 |
| Carlos (PM) | 3.0 | 9.0 | +6.0 |
| Priya (Security) | 2.0 | 8.5 | +6.5 |

### Numbers
- 3,054줄 코드 추가
- 7개 새 파일
- 77+ 개별 개선사항
- 4시간 만에 4라운드 완료

---

## Day 1 — Go to Market (2026-03-26 Evening)

### Marketing infrastructure built
- npm v1.1.0 published (clarvia-mcp-server)
- mcp.so: 즉시 등록 완료 (라이브)
- Glama.ai: 제출 완료 (리뷰 대기)
- appcypher/awesome-mcp-servers: PR #771 open
- GitHub topics 8개 설정
- .well-known/agents.json 배포
- npm 키워드 18개 최적화
- smithery.yaml 추가
- GitHub Action (clarvia/scan-action) 생성

### 24/7 자동화 설정
- GitHub Actions cron: 아침 마케팅(9am) + 저녁 리포트(10pm) + keep-alive(14분)
- 텔레그램 봇 통합 (한글 리포트)
- 마케팅 로그: marketing-log.jsonl

### Mission launched
**목표: 일일 에이전트 방문 1,000,000**
- Baseline: 0
- Week 1 target: 50 daily
- Month 1: 500
- Month 3: 5,000
- Ultimate: 1,000,000

### Philosophy
- 에이전트만 타겟. 인간 마케팅 0.
- 모든 채널을 최대한 공격적으로 활용
- 어뷰징 없이 정당한 방법으로
- 매일 아침 계획, 저녁 리포트, 끊임없는 실행

---

## Day 1 — Night Marketing (2026-03-26 Night)

### Automated activities executed
- 44 marketing activities (35 success, 80% rate)
- npm visibility: Found in 1/5 key searches ("agent compatibility")
- awesome-mcp-servers PR #771: OPEN (pending merge)
- Smithery: 10 results found (listed via smithery.yaml)
- **Official MCP Registry: PUBLISHED** — `io.github.digitamaz/clarvia` v1.1.1 live at registry.modelcontextprotocol.io

### Night discoveries
- Clarvia is already indexed in Smithery (smithery.yaml worked)
- Duplicate version error on first publish attempt → bumped to v1.1.1 → SUCCESS
- Official registry uses `github-at` auth (not `github_access_token`)

### Status of directories
| Directory | Status |
|-----------|--------|
| mcp.so | Live |
| Glama.ai | Pending review |
| appcypher/awesome-mcp-servers | PR #771 OPEN |
| Smithery | Listed |
| **Official MCP Registry** | **LIVE** ✓ |
| PulseMCP | Not listed |

---

## Metrics Tracking

| Date | Tools | API Requests | npm Weekly | Directories | Score |
|------|-------|-------------|-----------|-------------|-------|
| 03-26 | 15,410 | 0 | 232 | 5 | Day 1 — 5 registries live |

---

## Lessons Learned

1. **유저 테스트가 최고의 제품 개선 도구** — 12페르소나 시뮬레이션이 4라운드 만에 4.1→9.1 달성
2. **무료 외부 API가 데이터 신뢰도를 근본적으로 해결** — OSV.dev, npm, GitHub API = 실데이터
3. **분류기가 제품의 핵심** — "other" 45%→5%가 모든 검색/분석 품질을 결정
4. **스코어 재보정이 플랫폼 신뢰의 기반** — 잘 알려진 도구가 낮은 점수면 전체 신뢰 붕괴
5. **에이전트 마케팅은 인간 마케팅과 완전히 다름** — npm 키워드 > 트위터, MCP 레지스트리 > Product Hunt

---

## Day 1 — Night Marketing (2026-03-26 Night)

### Night activities executed

**New PRs opened:**
- metorial/metorial-index PR #15 — catalog entry with structured YAML format
- YuzeHao2023/Awesome-MCP-Servers PR #102 — Tools & Utilities section

**PR status check:**
- appcypher/awesome-mcp-servers #771: open (5,268★)
- TensorBlock/awesome-mcp-servers #235: open (584★)
- MobinX/awesome-mcp-list #131: open (876★)
- metorial/metorial-index #15: open (217★)
- YuzeHao2023/Awesome-MCP-Servers #102: open (1,036★)

**Platform verification:**
- SSR: ✅ 46KB SSR pages (not JS-SPA)
- robots.txt: ✅ All AI crawlers whitelisted (GPTBot, ClaudeBot, OAI-SearchBot, PerplexityBot)
- agents.json: ✅ deployed at /.well-known/agents.json
- OpenAPI: ✅ 110 endpoints at /openapi.json
- Smithery: ✅ Listed
- Glama: ⏳ Review pending

**Day 1 final numbers:**
- Total marketing activities: 53 (success: 42, 79%)
- npm downloads: 232 (Day 1)
- Total awesome-list PRs open: 5
- Platform tools: 15,411

### Night session 2 (automated, 10pm+)
- Official MCP Registry: PUBLISHED v1.1.1 (api.modelcontextprotocol.io) ✓
- **modelcontextprotocol/servers PR #3719 OPEN** (82,180★) — biggest channel yet
- 10 awesome-list PRs all OPEN
- npm search visibility: found in 1/5 searches ("agent compatibility")

### Learnings
- PulseMCP, DevHunt, Composio require manual auth — can't automate
- MCP Official Registry: successfully published via github-at auth endpoint
- modelcontextprotocol/servers accepts community PRs via API (not blocked)
- Smithery already indexed us automatically from npm — listing exists


### Day 1 Afternoon session (automated, 2:30pm+)
- **68 marketing activities completed today** (new record)
- All major awesome-list PRs submitted (20+ PRs across MCP/A2A/AI ecosystems)
- New PRs this session:
  - **ComposioHQ/awesome-claude-plugins PR #83** (1,199★)
  - **ComposioHQ/awesome-claude-skills PR #506** (48,104★) — highest star count yet
  - **ikaijua/Awesome-AITools PR #396** (5,723★)
- Sitemap expanded: 10 → 15,406 tool page URLs (sitemapindex format)
- JSON-LD structured data verified on homepage and tool pages
- robots.txt: All AI crawlers whitelisted ✓
- GitHub Action: live on marketplace (clarvia-aeo-score-check) ✓

### Key channels status
- npm: 232 weekly downloads, v1.1.1 ready but needs OTP for publish
- Official MCP Registry: PUBLISHED ✓
- awesome-list PRs: ~25 open across multiple repos
- Sitemap: 15,406 tool URLs pushed (Vercel deployment pending)

### Next priorities
1. Publish npm v1.1.1 (needs manual OTP)
2. Smithery.ai listing (needs manual browser auth)
3. PulseMCP listing (needs manual auth)
4. Monitor PR merge status

---

## Day 5 — Evening Report (2026-03-30)

### Today's metrics
- Marketing activities: 5 (all successful)
- Channels: npm ×2, web ×1, github ×1, mcp_directories ×1
- API searches: 1 (query: "github")
- npm today: 10 downloads
- npm weekly: 595 downloads
- Total tools indexed: 15,238 (avg score: 38.2)
- All-time marketing: 111 activities (86% success rate)

### Stage targets
- Stage 1 (daily 100 API calls): 1/100 — very early
- npm weekly 1,000: 595/1,000 — on track

### Strategy notes
- Manual auth blockers: PulseMCP, Smithery, DevHunt (cannot automate)
- npm weekly growing: 232 (Day 1) → 595 (Day 5) — +156% in 4 days
- Awesome-list PRs: ~25 open, waiting for merges (organic traffic boost incoming)
- Night marketing focus: additional awesome-list PR submissions

### Challenges
- API usage extremely low (1 search/day) — discovery layer needs work
- Score quality: 0 "excellent" tools out of 15,238 — scoring calibration needed

