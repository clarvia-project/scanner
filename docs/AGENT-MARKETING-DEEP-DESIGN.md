# Clarvia 에이전트 마케팅 딥 설계 + 실시간 도구 수집 시스템

> 작성일: 2026-04-01
> 목표: AI 에이전트가 Clarvia를 자동 발견·사용·추천하는 플라이휠 + 새 도구 실시간 유입 파이프라인
> 전제: 사이트 안정화 완료, 27K+ 도구 인덱싱, MCP 서버 v1.1.2 배포됨

---

## Part 1: 에이전트 마케팅 딥 설계

### 기존 마케팅 현황 진단

| 채널 | 상태 | 결과 |
|------|------|------|
| MCP 디렉토리 등록 | 4곳 등록 완료 | 설치수 미미 |
| awesome-list PR | 25+ 오픈 | 대부분 미머지 |
| npm 패키지 | v1.1.2, 595/주 | 실사용자 극소 |
| .well-known 표준 | 모두 구현 | 에이전트 자동발견 사례 0 |
| SEO/구조화 데이터 | 기본 구현 | AI 검색 인용 0건 확인 |

**핵심 진단**: 에이전트는 도구를 스스로 찾지 않는다. **인간 개발자가 설정해야** 에이전트가 쓴다.
따라서 마케팅 타겟은 두 단계:
1. **지금**: 에이전트를 설정하는 인간 개발자
2. **6개월 후**: 자율적으로 도구를 탐색하는 에이전트 런타임

---

### 전략 1: 개발자 워크플로우 침투 (Agent Configuration Moment)

> 개발자가 "어떤 MCP 서버 쓸까?" 결정하는 순간에 Clarvia가 있어야 한다.

#### 1A. Claude Code 네이티브 통합

**왜 중요**: Claude Code 사용자는 MCP 서버를 가장 활발히 사용하는 집단.

| 액션 | 설명 | 임팩트 |
|------|------|--------|
| Claude Code 스킬 배포 | `/clarvia-scan` 스킬을 claude-code-skills 리포에 PR | 높음 |
| mcp.json 원클릭 설정 가이드 | "3줄 복붙으로 에이전트에 Clarvia 연결" | 높음 |
| Claude Code 사용 예시 콘텐츠 | "Claude Code로 MCP 서버 품질 확인하는 법" | 중간 |

**구체적 실행**:
```json
// ~/.claude/mcp.json 에 추가하는 것 하나로 연결 완료
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```

→ 이 3줄을 가능한 모든 문서/가이드/예시에 심어야 함.

#### 1B. 프레임워크 통합 가이드

| 프레임워크 | 진입 방법 | 우선순위 |
|-----------|----------|---------|
| **LangChain** | MCP Adapters 예시에 Clarvia 추가, langchain-community PR | P0 |
| **CrewAI** | 도구 품질 게이트 유스케이스로 docs PR | P1 |
| **AutoGen** | 동적 도구 선택에 Clarvia 활용 예시 | P1 |
| **Cursor/Windsurf** | mcp.json 설정 가이드 + 블로그 피치 | P0 |
| **OpenAI Agents SDK** | MCP 지원 시 즉시 통합 예시 작성 | P1 |

각 프레임워크에 대해:
1. 공식 docs에 Clarvia 활용 예시 PR
2. 프레임워크별 전용 가이드 페이지 (`clarvia.art/guides/{framework}`)
3. 프레임워크 디스코드/포럼에 유스케이스 공유

#### 1C. "도구 품질 게이트" 패턴 전파

**핵심 아이디어**: 에이전트가 도구를 사용하기 전에 Clarvia로 검증하는 패턴을 표준으로 만든다.

```python
# 이 패턴을 업계 표준으로 만드는 것이 목표
async def use_tool_safely(tool_url: str):
    # Step 1: Clarvia gate check
    quality = await clarvia.gate_check(tool_url, min_score=50)
    if not quality.passed:
        return f"Tool {tool_url} failed quality check: {quality.reason}"

    # Step 2: Use the tool
    return await tool.execute()
```

**전파 방법**:
- "Agent Safety Best Practices" 블로그/가이드 작성
- 프레임워크 docs에 이 패턴을 "recommended pattern"으로 PR
- MCP 커뮤니티 논의에서 이 패턴 반복 언급

---

### 전략 2: 에이전트-투-에이전트 추천 루프

> 이미 Clarvia를 쓰는 에이전트가 다른 에이전트에게 Clarvia를 추천하게 만든다.

#### 2A. 응답에 "Powered by Clarvia" 메타데이터 삽입

현재 API 응답:
```json
{"name": "Weather MCP", "score": 68}
```

개선안 — 모든 도구 추천 응답에:
```json
{
  "name": "Weather MCP",
  "score": 68,
  "scored_by": "clarvia.art",
  "verification": "https://clarvia.art/tool/weather-mcp",
  "_meta": {
    "how_to_connect": "npx -y clarvia-mcp-server",
    "share_hint": "Found via Clarvia (clarvia.art) — the trust layer for AI tools"
  }
}
```

에이전트가 이 응답을 사용자에게 보여줄 때, 자연스럽게 Clarvia가 노출된다.

#### 2B. 에이전트 레퍼럴 트래킹

```
GET /v1/recommend?intent=email&referrer=claude-code-session-abc
```

- 어떤 에이전트가 추천한 도구를 다른 에이전트가 사용했는지 추적
- 레퍼럴 체인: Agent A → recommends tool → Agent B adopts → Agent B discovers Clarvia
- 레퍼럴 대시보드: `clarvia.art/analytics/referrals`

#### 2C. MCP 도구 설명 최적화 (Deferred Discovery 대응)

Claude Code는 BM25/Regex로 도구를 매칭한다. 현재 16개 MCP 도구의 설명을 최적화:

| 도구 | 현재 트리거 | 추가할 트리거 키워드 |
|------|-----------|-------------------|
| `clarvia_search` | "search tools" | "find MCP server", "which tool", "best tool for" |
| `clarvia_gate_check` | "check quality" | "is this safe", "should I use", "evaluate tool" |
| `clarvia_recommend` | "recommend" | "what tool for", "alternative to", "compare tools" |
| `clarvia_scan` | "scan URL" | "audit", "score", "rate this tool" |

**When to use / When not to use** 패턴 필수 추가:
```
When to use: When an agent needs to find, evaluate, or compare AI tools
When NOT to use: For general web search or non-tool queries
```

---

### 전략 3: 도구 메이커 플라이휠

> 도구 메이커가 Clarvia 점수를 올리려고 노력하면, 생태계 품질이 올라가고, 에이전트 가치가 올라간다.

#### 3A. 점수 알림 시스템 (Outbound)

```
Step 1: GitHub에서 새 MCP 서버 발견
Step 2: 자동 스캔 + AEO 점수 산출
Step 3: 해당 리포에 Issue 생성 (opt-in 기반)
  → "Your MCP server scored 42/100 on Clarvia AEO. Here's how to reach 70+:"
Step 4: 개선 플레이북 링크 제공
Step 5: 재스캔 후 점수 변화 알림
```

**GitHub Issue 템플릿**:
```markdown
## 🔍 Clarvia AEO Score Report

Your tool **{tool_name}** scored **{score}/100** on the Clarvia Agent Experience Optimization index.

### Quick Wins (estimated +15 points):
- [ ] Add OpenAPI spec (+5)
- [ ] Add MCP server definition (+7)
- [ ] Add install command to README (+3)

### Full report: https://clarvia.art/scan/{scan_id}
### Improve your score: https://clarvia.art/improve

---
*This is an automated quality report from [Clarvia](https://clarvia.art), the trust index for AI tools.
Not interested? Reply "unsubscribe" and we won't send future reports.*
```

#### 3B. Clarvia 배지 경제

현재: 배지 시스템 존재하지만 사용 제로.

**배지 2.0 설계**:
- 동적 SVG 배지 (실시간 점수 반영)
- "Clarvia Verified" 배지 (60+ 점수)
- "Clarvia Top 100" 배지 (리더보드 상위)
- GitHub README에 배지 추가 시 → Clarvia 백링크 자동 생성

**배지 배포 자동화**:
1. 상위 1,000개 도구의 GitHub 리포 식별
2. 각 리포에 "Add Clarvia badge" PR 자동 생성
3. PR 설명에 점수 + 개선 가이드 포함

⚠️ **주의**: GitHub 배지 PR 대량 제출은 이전에 GitHub 플래그 원인이었음.
→ **일일 5건 이하**, 고점수(60+) 도구만 대상, 개인화된 PR 메시지.

#### 3C. 도구 메이커 대시보드

`clarvia.art/maker/{github_handle}`

- 내 도구들의 점수 한눈에 보기
- 시간별 점수 변화 그래프
- 구체적 개선 액션 목록
- "Claim this tool" → 소유권 인증 후 알림 설정
- 경쟁 도구와 비교 기능

---

### 전략 4: AI 검색 엔진 최적화 (AEO for Clarvia itself)

> Perplexity, ChatGPT Search, Google AI Overview에서 "best MCP server for X" 질문에 Clarvia가 인용되게.

#### 4A. 프로그래매틱 SEO 강화

현재 27K+ 도구 페이지가 있지만, AI 검색엔진이 인용하지 않는 이유:
- 페이지 내용이 너무 짧음 (점수 + 기본 정보만)
- 비교/맥락 정보 부족
- FAQ 없음

**개선안**:
각 도구 페이지에 자동 생성:
```
/tool/{id} 페이지 구조:
├── AEO 점수 + 등급 (기존)
├── "What is {tool_name}?" (자동 생성 설명)
├── "Who should use {tool_name}?" (타겟 사용자)
├── "How to install" (설치 가이드)
├── "Alternatives to {tool_name}" (경쟁 도구 비교)
├── "Clarvia AEO Score Breakdown" (점수 상세)
└── FAQ (Schema.org JSON-LD)
    ├── "Is {tool_name} safe to use with AI agents?"
    ├── "How does {tool_name} compare to {competitor}?"
    └── "What AEO score does {tool_name} have?"
```

#### 4B. "Best MCP Server for X" 랭킹 페이지

카테고리별 자동 생성 랭킹 페이지:
```
clarvia.art/best/email        → "Best MCP Servers for Email (2026)"
clarvia.art/best/database     → "Best Database Tools for AI Agents"
clarvia.art/best/web-search   → "Best Web Search MCP Servers Compared"
```

각 페이지에:
- Top 10 도구 비교표
- 점수별 정렬
- 장단점 요약
- 설치 가이드
- JSON-LD 구조화 데이터

→ AI 검색엔진이 "best MCP server for email" 질문에 이 페이지를 인용.

#### 4C. 콘텐츠 리치니스 (E-E-A-T)

- `/blog/state-of-mcp-{year}-{month}` — 월간 MCP 생태계 리포트
- `/blog/aeo-methodology` — 스코어링 방법론 투명 공개
- `/blog/case-study/{tool}` — 점수 개선 성공 사례

---

### 전략 5: 커뮤니티 & 네트워크 효과

#### 5A. MCP 커뮤니티 침투

| 커뮤니티 | 액션 | 주기 |
|---------|------|------|
| Anthropic Discord (#mcp) | Clarvia 활용 팁 공유, 질문 답변 | 주 2-3회 |
| r/ClaudeAI | "MCP 서버 품질 확인법" 유스케이스 포스트 | 월 2회 |
| Hacker News | 생태계 리포트 Show HN | 분기 1회 |
| Dev.to / Medium | "Agent Tool Selection Best Practices" | 월 1회 |
| X (Twitter) | 새 고점수 도구 발견 공유, MCP 트렌드 | 주 3회 |

#### 5B. 에이전트 개발자 워크숍

- "Build an Agent with Quality Gates" 온라인 워크숍
- Clarvia를 활용한 도구 선택 파이프라인 구축 실습
- 워크숍 자료 자체가 마케팅 자산

#### 5C. 파트너십

| 파트너 타입 | 대상 | 가치 교환 |
|-----------|------|----------|
| MCP 프레임워크 | LangChain, CrewAI | 통합 예시 제공 ↔ 공식 추천 |
| 호스팅 | Smithery, Glama | 점수 데이터 제공 ↔ 프리미엄 배치 |
| 교육 | AI 부트캠프 | 무료 Pro 티어 ↔ 커리큘럼 포함 |

---

### 마케팅 실행 로드맵

#### Week 1-2 (4월 1주~2주): Foundation

| # | 작업 | 담당 | KPI |
|---|------|------|-----|
| 1 | MCP 도구 설명 키워드 최적화 (16개 전체) | 자동 | 도구 선택율 |
| 2 | Claude Code 스킬 PR 제출 | 수동 | PR 승인 |
| 3 | 도구 페이지 리치화 (FAQ, 비교, 설치 가이드) | 자동 | 페이지당 체류시간 |
| 4 | "Best MCP for X" 랭킹 페이지 10개 생성 | 자동 | AI 검색 인용 |
| 5 | 응답 메타데이터에 share_hint 추가 | 자동 | 레퍼럴 트래킹 |

#### Week 3-4 (4월 3주~4주): Outreach

| # | 작업 | 담당 | KPI |
|---|------|------|-----|
| 6 | LangChain/CrewAI 통합 가이드 PR | 수동 | PR 승인 |
| 7 | 도구 메이커 상위 50개에 점수 알림 | 자동 | 응답률 |
| 8 | Cursor/Windsurf 설정 가이드 발행 | 자동 | 가이드 조회수 |
| 9 | 커뮤니티 포스트 (Reddit, Discord) 3건 | 수동 | 인게이지먼트 |
| 10 | 월간 MCP 생태계 리포트 발행 | 자동 | 공유수 |

#### Month 2 (5월): Scale

| # | 작업 | 담당 | KPI |
|---|------|------|-----|
| 11 | 배지 PR 자동화 (일 5건, 고점수만) | 자동 | 배지 노출수 |
| 12 | 도구 메이커 대시보드 MVP | 빌드 | 메이커 등록수 |
| 13 | 에이전트 레퍼럴 대시보드 | 빌드 | 레퍼럴 체인 수 |
| 14 | Show HN: "State of MCP Quality 2026" | 수동 | HN 포인트 |

---

### KPI 대시보드

| 지표 | 현재 | 4월 말 | 7월 |
|------|------|--------|-----|
| 일일 API 호출 | ~100 (대부분 봇) | 500 | 5,000 |
| 고유 에이전트 세션/일 | 0 | 10 | 100 |
| npm 주간 다운로드 | 595 | 1,500 | 5,000 |
| 배지 외부 노출/일 | 0 | 50 | 500 |
| 도구 메이커 방문/주 | 0 | 20 | 200 |
| AI 검색 인용 | 0 | 5 | 50 |
| 프레임워크 공식 통합 | 0 | 1 | 3 |

---

## Part 2: 실시간 도구 수집 시스템 설계

### 현재 상태

- 27,844개 도구 인덱싱 완료 (일괄 수집)
- `/v1/submit` API 존재하지만 외부 사용 0건
- 새 도구 추가 = 수동 배치 실행
- MCP 생태계에서 매주 100-200개 새 서버가 출현

### 문제

1. **새 도구 반영 지연**: 배치 수집 → 수일~수주 지연
2. **트렌딩 도구 누락**: 핫한 새 MCP 서버가 며칠간 미인덱싱
3. **도구 메이커 셀프서비스 부재**: submit API는 있으나 파이프라인이 불완전
4. **죽은 도구 정리 없음**: deprecated/삭제된 도구가 카탈로그에 잔존

---

### 아키텍처: 4-Source Ingestion Pipeline

```
┌─────────────────────────────────────────────────────┐
│                INGESTION SOURCES                     │
├──────────┬──────────┬──────────┬───────────────────── │
│  Source 1 │ Source 2 │ Source 3 │ Source 4            │
│  GitHub   │ Registry │ Self-    │ Community           │
│  Watch    │ Sync     │ Submit   │ Crawl               │
└────┬─────┴────┬─────┴────┬─────┴────┬────────────────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────┐
│              INGESTION QUEUE                         │
│  (in-memory queue + JSONL persistence)               │
│  Dedup by URL/name → Priority scoring                │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              PROCESSING PIPELINE                     │
│  1. URL validation & normalization                   │
│  2. Metadata extraction (GitHub API, npm API, etc)   │
│  3. AEO scoring (existing scorer)                    │
│  4. Dedup check against existing catalog             │
│  5. Quality gate (score > 10 to index)               │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              CATALOG UPDATE                          │
│  - Merge into collected-tools-*.jsonl                │
│  - Update search index                              │
│  - Trigger cache invalidation                        │
│  - Log to ingestion-log.jsonl                        │
└─────────────────────────────────────────────────────┘
```

---

### Source 1: GitHub Watcher

**목적**: GitHub에서 새로 생성되는 MCP 서버를 실시간으로 감지

**메커니즘**:
```python
# 스케줄: 6시간마다 실행
async def github_watch():
    # 1. GitHub Search API로 새 MCP 리포 탐색
    queries = [
        "mcp-server created:>={yesterday} language:TypeScript",
        "mcp-server created:>={yesterday} language:Python",
        "model-context-protocol created:>={yesterday}",
        "topic:mcp-server created:>={yesterday}",
    ]

    # 2. 새 릴리즈 감지 (기존 인덱싱된 리포의 새 버전)
    for tool in top_1000_tools:
        releases = await github.get_latest_release(tool.repo)
        if releases.published_at > tool.last_checked:
            queue.add(tool.url, priority="update", source="github_release")

    # 3. Trending 리포 체크
    trending = await github.trending(language="typescript", since="daily")
    for repo in trending:
        if is_mcp_related(repo):
            queue.add(repo.url, priority="high", source="github_trending")
```

**Rate Limit 관리**:
- GitHub API: 5,000 req/hour (authenticated)
- 일일 4회 실행 × ~200 requests = 800 req/day (여유 충분)

### Source 2: Registry Sync

**목적**: MCP 레지스트리(mcp.so, Smithery, Glama, Official)의 새 등록을 동기화

```python
# 스케줄: 12시간마다 실행
async def registry_sync():
    registries = {
        "mcp_official": "https://registry.modelcontextprotocol.io/api/servers",
        "smithery": "https://smithery.ai/api/servers?sort=newest",
        "glama": "https://glama.ai/api/mcp/servers?sort=created",
        "pulsemcp": "https://pulsemcp.com/api/servers",
    }

    for name, url in registries.items():
        servers = await fetch_registry(url)
        for server in servers:
            if not already_indexed(server.npm_name or server.github_url):
                queue.add(
                    url=server.url,
                    priority="medium",
                    source=f"registry:{name}",
                    metadata=server.raw_data
                )
```

### Source 3: Self-Submit Pipeline (기존 `/v1/submit` 강화)

**현재 문제**: submit 후 실제 스캔/인덱싱 파이프라인이 불완전

**개선안**:
```
POST /v1/submit
  ↓
1. URL 유효성 검증 (200 OK, 중복 체크)
  ↓
2. 큐에 즉시 추가 (priority: "self_submit")
  ↓
3. 스캔 (기존 스코어러)
  ↓
4. 점수 > 10이면 카탈로그에 추가
  ↓
5. 웹훅/이메일로 결과 알림
  ↓
6. 응답: {submission_id, status, estimated_time: "5-15min"}
```

**새 엔드포인트**:
```
POST /v1/submit          — 도구 제출 (기존 강화)
GET  /v1/submit/status/{id} — 진행 상황 실시간 조회
POST /v1/submit/bulk     — 최대 50개 일괄 제출 (Pro 전용)
```

### Source 4: Community Crawl

**목적**: npm, PyPI, awesome-list 등 커뮤니티 소스에서 새 도구 발견

```python
# 스케줄: 24시간마다 실행
async def community_crawl():
    # npm 새 패키지
    npm_results = await npm_search("mcp-server", size=100, sort="created")

    # PyPI 새 패키지
    pypi_results = await pypi_search("mcp", sort="newest")

    # awesome-list 변경 감지
    for awesome_repo in AWESOME_REPOS:
        diff = await github.compare(awesome_repo, since=last_crawl)
        new_tools = parse_awesome_diff(diff)
        for tool in new_tools:
            queue.add(tool.url, priority="medium", source="awesome_list")
```

---

### Ingestion Queue 설계

```python
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class Priority(Enum):
    CRITICAL = 0   # 트렌딩, 수동 요청
    HIGH = 1       # GitHub trending, self-submit
    MEDIUM = 2     # Registry sync, awesome-list
    LOW = 3        # 주기적 크롤, 재스캔
    UPDATE = 4     # 기존 도구 업데이트 체크

@dataclass
class IngestionItem:
    url: str
    source: str          # "github_watch", "registry:smithery", "self_submit", etc.
    priority: Priority
    metadata: dict       # 소스별 추가 데이터
    submitted_at: datetime
    retry_count: int = 0

class IngestionQueue:
    """메모리 큐 + JSONL 영속화. Render 512MB 제약 하에 동작."""

    def __init__(self, max_size=5000):
        self._queue: list[IngestionItem] = []
        self._seen_urls: set[str] = set()  # 중복 방지
        self._persistence = Path("data/ingestion-queue.jsonl")

    def add(self, url: str, source: str, priority: Priority, metadata: dict = None):
        normalized = normalize_url(url)
        if normalized in self._seen_urls:
            return  # 중복 스킵

        item = IngestionItem(
            url=normalized, source=source, priority=priority,
            metadata=metadata or {}, submitted_at=datetime.utcnow()
        )
        self._queue.append(item)
        self._seen_urls.add(normalized)
        self._persist(item)

    def next_batch(self, size=10) -> list[IngestionItem]:
        """우선순위 순으로 다음 배치 반환"""
        self._queue.sort(key=lambda x: (x.priority.value, x.submitted_at))
        batch = self._queue[:size]
        self._queue = self._queue[size:]
        return batch
```

---

### Processing Pipeline 상세

```python
async def process_ingestion_batch(batch: list[IngestionItem]):
    results = []
    for item in batch:
        try:
            # 1. URL 검증
            if not await validate_url(item.url):
                log_skip(item, "invalid_url")
                continue

            # 2. 중복 체크 (기존 카탈로그)
            existing = find_existing_tool(item.url)
            if existing and item.source != "update":
                log_skip(item, "duplicate")
                continue

            # 3. 메타데이터 추출
            metadata = await extract_metadata(item.url)
            # GitHub: stars, last_commit, topics, language
            # npm: downloads, version, dependencies
            # PyPI: downloads, version, classifiers

            # 4. AEO 스코어링
            score = await score_tool(item.url, metadata)

            # 5. 품질 게이트
            if score.total < 10:
                log_skip(item, f"low_score:{score.total}")
                continue

            # 6. 카탈로그에 추가/업데이트
            tool_entry = build_tool_entry(item, metadata, score)
            await upsert_to_catalog(tool_entry)

            results.append({
                "url": item.url,
                "source": item.source,
                "score": score.total,
                "status": "indexed"
            })

        except Exception as e:
            if item.retry_count < 3:
                item.retry_count += 1
                queue.add_back(item)  # 재시도
            else:
                log_error(item, str(e))

    # 7. 인덱스 갱신
    await rebuild_search_index()
    await invalidate_caches()

    # 8. 로그
    log_ingestion_results(results)
    return results
```

---

### 스케줄 통합

```
┌─────────────────────────────────────────┐
│          SCHEDULED TASKS                 │
├──────────┬──────────────────────────────┤
│ 6시간    │ GitHub Watcher               │
│ 12시간   │ Registry Sync                │
│ 24시간   │ Community Crawl              │
│ 1시간    │ Process Queue (batch=20)     │
│ 24시간   │ Dead Tool Cleanup            │
│ 7일      │ Full Rescan (top 1000)       │
└──────────┴──────────────────────────────┘
```

### Dead Tool Cleanup

```python
# 스케줄: 24시간마다
async def cleanup_dead_tools():
    """죽은 도구를 archived로 마킹"""
    for tool in get_all_tools():
        if tool.last_checked < (now - timedelta(days=90)):
            # 90일 이상 미확인 → 라이브 체크
            alive = await probe_url(tool.url)
            if not alive:
                tool.status = "archived"
                tool.archived_reason = "unreachable_90d"
                await update_tool(tool)
```

---

### API 엔드포인트 (신규/수정)

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/v1/submit` | 도구 제출 (강화) |
| `GET` | `/v1/submit/status/{id}` | 제출 상태 조회 |
| `POST` | `/v1/submit/bulk` | 일괄 제출 (Pro) |
| `GET` | `/v1/ingestion/stats` | 수집 통계 |
| `GET` | `/v1/ingestion/recent` | 최근 추가된 도구 |
| `GET` | `/v1/tools/new` | 신규 도구 피드 (RSS 호환) |
| `GET` | `/v1/tools/trending` | 트렌딩 도구 |

### Render 메모리 예산 (512MB 제약)

| 구성요소 | 메모리 |
|---------|--------|
| 기존 카탈로그 + 캐시 | ~250MB |
| 수집 큐 (max 5,000) | ~5MB |
| 처리 파이프라인 | ~20MB |
| seen_urls 셋 (50K) | ~10MB |
| 여유 | ~227MB |

→ 충분. 큐 사이즈를 5,000으로 제한하면 메모리 안전.

---

### 프론트엔드 연동

`clarvia.art/new` — 최근 추가된 도구 페이지
```
- 24시간 이내 새로 인덱싱된 도구 목록
- 소스별 필터 (GitHub, Registry, Submit, Crawl)
- "Submit Your Tool" CTA 버튼
- 실시간 업데이트 (polling 30초)
```

`clarvia.art/trending` — 트렌딩 도구 페이지
```
- 지난 7일간 점수 상승 Top 20
- 새로 등장한 고점수(60+) 도구
- GitHub 스타 급증 도구
```

---

## Part 3: 통합 실행 우선순위

### P0 — 이번 주 (4/1~4/7)

1. **MCP 도구 설명 최적화** — 16개 도구 전체 키워드/트리거 개선
2. **응답 메타데이터 share_hint 추가** — 에이전트→인간 노출 경로
3. **Ingestion Queue 구현** — 기본 큐 + GitHub Watcher
4. **"Best MCP for X" 페이지 5개** — AI 검색 인용 유도

### P1 — 다음 주 (4/8~4/14)

5. **Registry Sync** — 4개 레지스트리 자동 동기화
6. **Submit 파이프라인 완성** — 제출→스캔→인덱싱 자동화
7. **도구 페이지 리치화** — FAQ, 비교, 설치 가이드 자동 생성
8. **프레임워크 가이드** — LangChain, Cursor 설정 가이드

### P2 — 4월 후반

9. **Community Crawl** — npm/PyPI 새 패키지 감지
10. **도구 메이커 점수 알림** — 상위 50개 대상
11. **Dead Tool Cleanup** — 미응답 도구 아카이브
12. **배지 2.0** — 동적 SVG + 자동 PR (일 5건)

---

## 성공 기준

| 시점 | 마케팅 성공 | 수집 시스템 성공 |
|------|-----------|----------------|
| 4월 말 | 일 500 API 호출, 에이전트 세션 10/일 | 주 100+ 신규 도구 자동 수집 |
| 6월 말 | 일 5,000 API 호출, npm 5K/주 | 신규 도구 평균 24시간 내 인덱싱 |
| 9월 | Pro 유료 고객 10명, MRR $500 | MCP 생태계 95% 커버리지 |
