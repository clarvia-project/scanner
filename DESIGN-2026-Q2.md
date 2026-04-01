# Clarvia Q2 2026 실행 설계서

> 목표: 100만 에이전트 일일 사용 + 6월 Pro 런칭 ($500 MRR)
> 작성: 2026-04-01
> 모델: claude-opus-4-6[1m]

---

## 전체 타임라인

```
4월 1주 (4/1-4/6)   Sprint 1: 데이터 품질 기반
4월 2주 (4/7-4/13)  Sprint 2: 어트리뷰션 + 응답 리치화
4월 3주 (4/14-4/20) Sprint 3: 라이브 프로빙 파이프라인
4월 4주 (4/21-4/27) Sprint 4: UI 통합 + 버그 수정
5월 1주 (4/28-5/4)  Sprint 5: 의미 검색 + 워크플로우 MCP
5월 2주 (5/5-5/11)  Sprint 6: 증거 엔드포인트 + 트렌드
5월 3주 (5/12-5/18) Sprint 7: 마케팅 루프 자동화
5월 4주 (5/19-5/25) Sprint 8: Pro 티어 준비
6월 1주 (5/26-6/1)  Sprint 9: Pro 런칭 + 도구 메이커 접촉
6월 2주 (6/2-6/8)   Sprint 10: Enterprise 베타 + 웹훅
```

---

## Sprint 1: 데이터 품질 기반 (4/1-4/6)

### Task 1.1: 레거시 스코어러 정리

**현재 상태**: `scoring/__init__.py`가 이미 통합 라우터 역할. `tool_scorer.py`는 레거시 프록시.

**작업**:
```
파일: backend/app/tool_scorer.py
변경: normalize_tool() 내부를 scoring/__init__.py::score_tool()로 완전 위임
      레거시 5차원(20/20/20/25/15) 코드 제거
      backward-compat 래퍼만 유지 (호출하는 곳이 있을 수 있으므로)

파일: backend/app/scoring/__init__.py
변경: detect_tool_type() 개선
      - source 필드 활용 강화 (현재 "unknown" → 수집 시점에 태깅 필요)
      - fallback을 "general"이 아닌 실제 분석 기반으로

검증: python3 -m pytest tests/ --tb=short (53개 전부 PASS)
```

**예상 공수**: 2-3시간

### Task 1.2: Source 어트리뷰션 태깅

**현재 상태**: 모든 레코드의 source가 "unknown". 수집 파이프라인에서 태깅 안 됨.

**작업**:
```
파일: backend/app/scoring/__init__.py
변경: score_tool() 반환값에 source 필드 추가
      detect_source(raw_data) 함수 신규:
        - has "server" key → "mcp_registry"
        - raw_data.get("_source") 존재하면 사용
        - url contains "apis.guru" → "apis_guru"
        - url contains "composio" → "composio"
        - url contains "n8n" → "n8n"
        - npm_url 존재 → "npm"
        - github url 존재 → "github"
        - else → "community"

파일: backend/data/prebuilt-scans.json 재생성 시
변경: 각 레코드에 source 필드 포함

파일: scripts/scan_mcp_parallel.py, scan_glama_parallel.py, scan_github_parallel.py
변경: 수집 시 _source 필드 명시적 태깅
      - scan_mcp_parallel.py → _source: "mcp_registry"
      - scan_glama_parallel.py → _source: "glama"
      - scan_github_parallel.py → _source: "github"

파일: backend/app/routes/index_routes.py
변경: _compact_service(), _full_service()에 source 필드 노출
```

**예상 공수**: 4-5시간

### Task 1.3: Scoring Confidence 필드

**현재 상태**: 없음. 점수만 있고 "이 점수를 얼마나 믿어도 되는지" 정보 없음.

**작업**:
```
파일: backend/app/scoring/__init__.py
변경: score_tool() 반환값에 scoring_confidence (0-100) 추가

confidence 계산 로직:
  base = 0
  + 20 if has_description and len(description) > 50
  + 15 if has_homepage or has_url
  + 15 if has_repository (github/gitlab)
  + 15 if has_version
  + 10 if has_npm_url or has_pypi_url
  + 10 if npm_quality_score exists
  + 5  if has_keywords and len(keywords) >= 3
  + 5  if has_license
  + 5  if updated_within_6_months
  = min(100, sum)

파일: backend/app/routes/index_routes.py
변경: _compact_service()에 scoring_confidence 필드 추가
      _full_service()에 confidence_breakdown 추가

파일: mcp-server/src/index.ts
변경: Service 인터페이스에 scoring_confidence 추가
```

**예상 공수**: 3-4시간

### Task 1.4: 저품질 도구 아카이브 정책

**현재 상태**: 30점 미만 도구가 약 20%+. 검색 결과 품질 저하.

**작업**:
```
파일: backend/app/routes/index_routes.py
변경: 기본 검색(/v1/services)에서 min_score 기본값 20 적용
      source=all일 때만 전체 노출
      archived 도구는 별도 필터 (archived=true)

      _ensure_loaded() 수정:
        - score < 20 AND updated_at > 6개월 → archived 플래그
        - 검색 기본값에서 archived 제외
        - /v1/stats에 archived_count 추가

규칙:
  - archived 도구는 삭제하지 않음 (데이터 모트 보존)
  - 직접 scan_id로 접근하면 여전히 조회 가능
  - "archived" 라벨 표시
```

**예상 공수**: 2-3시간

### Sprint 1 배포 체크리스트
- [ ] pytest 53개 PASS
- [ ] /v1/services 응답에 source, scoring_confidence 포함 확인
- [ ] /v1/stats에 archived_count 포함 확인
- [ ] Render 배포 후 라이브 API 확인

---

## Sprint 2: 어트리뷰션 + 응답 리치화 (4/7-4/13)

### Task 2.1: 마케팅 어트리뷰션 추적 시스템

**현재 상태**: analytics_writer.py에 요청 기록 있으나, "어디서 왔는가" 추적 불가.

**작업**:
```
파일: backend/app/services/analytics_writer.py
변경: build_analytics_entry()에 어트리뷰션 필드 추가

추가 필드:
  - referrer: request.headers.get("Referer", "direct")
  - utm_source: query params에서 추출 (utm_source, utm_medium, utm_campaign)
  - entry_point: 첫 번째 접근 엔드포인트 (세션 기준)
  - mcp_client: MCP tool call이면 클라이언트 식별

referrer 분류 로직:
  "smithery.ai" → "smithery"
  "glama.ai" → "glama"
  "npmjs.com" → "npm"
  "github.com" → "github"
  "google.com" → "google_search"
  contains "clarvia" → "internal"
  else → "other"

파일: backend/app/middleware.py
변경: AnalyticsMiddleware에서 referrer, utm 파라미터 추출하여 analytics_writer로 전달

파일: backend/app/routes/analytics_routes.py
변경: 신규 엔드포인트 추가
  GET /api/admin/analytics/attribution
    → 채널별 트래픽, 전환율 (검색→상세→스캔 퍼널)
    → 기간: 7d, 30d, 90d
    → 응답: { channels: [{name, visits, conversions, conversion_rate}] }

Supabase 스키마:
  analytics_events 테이블에 컬럼 추가:
    referrer TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT
```

**예상 공수**: 5-6시간

### Task 2.2: 응답 스키마 데이터 채우기

**현재 상태**: standard 응답에 pricing/capabilities/difficulty 필드 있으나 대부분 null.

**작업**:
```
파일: backend/app/scoring/__init__.py
변경: score_tool() 결과에 enrichment 데이터 자동 추출

pricing 추출:
  - description에서 "free", "open-source", "premium", "$" 키워드 탐지
  - npm metadata의 license → "MIT"/"Apache" = free, "proprietary" = paid
  - 결과: "free" | "freemium" | "paid" | "open_source" | "unknown"

capabilities 추출:
  - MCP server: tools 리스트에서 tool names 추출
  - API: OpenAPI spec에서 주요 엔드포인트 추출 (최대 10개)
  - CLI: description에서 동사+목적어 패턴 추출
  - 결과: ["search", "create", "delete", "monitor", ...] (최대 10개)

difficulty 추출:
  - has npm_url + install_cmd → "easy"
  - has docker/self-host keywords → "moderate"
  - needs compilation/custom setup → "advanced"
  - 결과: "easy" | "moderate" | "advanced" | "unknown"

install_command 생성:
  - npm: "npx clarvia-mcp-server" 또는 "npm install package-name"
  - pip: "pip install package-name"
  - docker: "docker run image-name"
  - 결과: 바로 복사 가능한 설치 명령어

파일: backend/app/routes/index_routes.py
변경: _compact_service()에서 enrichment 데이터 포함
      null인 필드는 score_tool() 재실행 없이 런타임 추론

파일: scripts/enrich_existing.py (신규)
용도: 기존 15,274개 도구에 pricing/capabilities/difficulty 일괄 추가
      prebuilt-scans.json 재생성
```

**예상 공수**: 6-8시간

### Task 2.3: 채택률 데이터 통합

**현재 상태**: npm downloads, GitHub stars 데이터 수집 안 됨.

**작업**:
```
파일: backend/app/services/popularity_service.py (신규)
용도: 외부 소스에서 채택률 데이터 수집

class PopularityService:
    async def get_npm_downloads(package_name: str) -> int:
        # GET https://api.npmjs.org/downloads/point/last-week/{package}
        # 캐시: 24시간 TTL

    async def get_github_stars(repo_url: str) -> int:
        # GET https://api.github.com/repos/{owner}/{repo}
        # 캐시: 24시간 TTL
        # Rate limit 주의: 60/hour (unauthenticated)

    async def get_pypi_downloads(package_name: str) -> int:
        # GET https://pypistats.org/api/packages/{package}/recent
        # 캐시: 24시간 TTL

    def compute_popularity_score(downloads, stars) -> int:
        # 0-100 정규화
        # npm: log10(downloads) * 15 (capped at 60)
        # stars: log10(stars) * 20 (capped at 40)
        # 합산 후 min(100, total)

파일: backend/app/routes/index_routes.py
변경: _full_service()에 popularity_data 섹션 추가
      {npm_weekly: int, github_stars: int, pypi_monthly: int, popularity_score: int}

파일: scripts/batch_popularity.py (신규)
용도: 매일 6am 상위 2,000개 도구의 채택률 데이터 수집
      결과를 backend/data/popularity-cache.json에 저장
      API 시작 시 로드

주의: GitHub API rate limit (60/hour unauthenticated)
      → GITHUB_TOKEN 환경변수로 5,000/hour 확보
      → 2,000개 도구를 6시간에 걸쳐 분산 요청
```

**예상 공수**: 6-8시간

### Sprint 2 배포 체크리스트
- [ ] /api/admin/analytics/attribution 동작 확인
- [ ] /v1/services 응답에 pricing, capabilities, difficulty 비-null 비율 50%+ 확인
- [ ] popularity-cache.json 생성 확인
- [ ] pytest PASS + Render 배포

---

## Sprint 3: 라이브 프로빙 파이프라인 (4/14-4/20)

### Task 3.1: 라이브 프로빙 서비스

**현재 상태**: accessibility_probes 테이블 존재. /api/v1/accessibility-probe 엔드포인트 부분 존재. 그러나 자동 주기적 프로빙 없음.

**작업**:
```
파일: backend/app/services/live_prober.py (신규)
용도: 도구의 실시간 상태를 주기적으로 확인

class LiveProber:
    async def probe_service(url: str) -> ProbeResult:
        """단일 도구 프로빙 (5초 타임아웃)"""
        result = {
            "url": url,
            "probed_at": datetime.utcnow().isoformat(),
            "reachable": False,
            "response_time_ms": None,
            "status_code": None,
            "has_json_response": False,
            "has_openapi": False,
            "has_mcp": False,
            "has_agents_json": False,
            "ssl_valid": False,
            "ssl_expiry_days": None,
        }

        # Step 1: HEAD request (reachability + latency)
        start = time.monotonic()
        response = await session.head(url, timeout=5)
        result["response_time_ms"] = (time.monotonic() - start) * 1000
        result["reachable"] = response.status < 500
        result["status_code"] = response.status

        # Step 2: Content-Type 확인
        if "application/json" in response.headers.get("content-type", ""):
            result["has_json_response"] = True

        # Step 3: 병렬 탐색 (3개 동시)
        checks = await asyncio.gather(
            self._check_openapi(session, url),     # /openapi.json
            self._check_mcp(session, url),          # MCP registry lookup
            self._check_agents_json(session, url),  # /.well-known/agents.json
            return_exceptions=True
        )

        # Step 4: SSL 인증서 확인
        result["ssl_valid"], result["ssl_expiry_days"] = await self._check_ssl(url)

        return result

    async def probe_batch(urls: list[str], concurrency=10) -> list[ProbeResult]:
        """배치 프로빙 (동시 10개)"""
        semaphore = asyncio.Semaphore(concurrency)
        async def _limited(url):
            async with semaphore:
                return await self.probe_service(url)
        return await asyncio.gather(*[_limited(u) for u in urls])

파일: backend/app/services/probe_scheduler.py (신규)
용도: 주기적 프로빙 스케줄링

PROBE_SCHEDULE:
  - 상위 500개 (score >= 60): 매 6시간
  - 중위 1,000개 (score 35-59): 매 24시간
  - 하위: 프로빙 안 함 (요청 시에만)

저장:
  - Supabase accessibility_probes 테이블 upsert
  - 로컬 캐시: backend/data/probe-cache.json (최근 결과)
  - 30일 히스토리 유지 → uptime_30d 계산 가능

파일: backend/app/main.py
변경: lifespan에 probe_scheduler 백그라운드 태스크 등록
      startup 시 probe-cache.json 로드

파일: backend/app/routes/index_routes.py
변경: _compact_service()에 라이브 데이터 추가
  {
    "is_online": bool,
    "last_checked": "2026-04-15T12:00:00Z",
    "response_time_ms": 145,
    "uptime_30d": 99.2
  }

  _full_service()에 probe_history 추가
  {
    "probe_history": [
      {"date": "2026-04-15", "uptime": 100, "avg_latency_ms": 132},
      {"date": "2026-04-14", "uptime": 95.8, "avg_latency_ms": 201},
      ...
    ]
  }
```

**예상 공수**: 8-10시간

### Task 3.2: 프로빙 결과를 점수에 반영

**현재 상태**: 점수가 메타데이터 기반. 실측 데이터 미반영.

**작업**:
```
파일: backend/app/scoring/__init__.py
변경: score_tool()에 optional probe_data 파라미터 추가

probe_bonus 계산 (최대 +10, 기존 100점 위에):
  + 3 if reachable and response_time_ms < 500
  + 2 if has_openapi
  + 2 if has_mcp
  + 1 if has_agents_json
  + 2 if uptime_30d >= 99.0

  반대로 감점:
  - 5 if not reachable (최근 프로빙에서)
  - 3 if response_time_ms > 5000
  - 2 if uptime_30d < 90.0

최종 점수: max(0, min(100, base_score + probe_bonus))

주의: probe_data가 없으면 (프로빙 안 된 도구) bonus = 0, 감점 없음
      → 기존 점수 체계 유지, 프로빙된 도구만 점수 조정
```

**예상 공수**: 3-4시간

### Sprint 3 배포 체크리스트
- [ ] probe_scheduler 백그라운드 실행 확인 (로그)
- [ ] 상위 500개 도구 첫 프로빙 완료
- [ ] /v1/services 응답에 is_online, last_checked 포함
- [ ] probe-cache.json 생성 확인
- [ ] Render 메모리 사용량 확인 (512MB 이내)

---

## Sprint 4: UI 통합 + 버그 수정 (4/21-4/27)

### Task 4.1: Nav 컴포넌트 나머지 15개 페이지 적용

**작업**:
```
적용 대상 (15개):
  frontend/app/compare/page.tsx
  frontend/app/tool/[id]/page.tsx
  frontend/app/profile/[id]/page.tsx
  frontend/app/leaderboard/page.tsx
  frontend/app/docs/page.tsx
  frontend/app/trending/page.tsx
  frontend/app/guide/page.tsx
  frontend/app/service/[id]/page.tsx
  frontend/app/register/page.tsx
  frontend/app/privacy/page.tsx
  frontend/app/methodology/page.tsx
  frontend/app/marketing/page.tsx
  frontend/app/pricing/page.tsx
  frontend/app/for-agents/page.tsx
  frontend/app/about/page.tsx

각 파일:
  1. import Nav from '@/app/components/Nav'
  2. 기존 인라인 헤더 코드 제거
  3. <Nav /> 컴포넌트로 교체
  4. 모바일 반응형 확인
```

**예상 공수**: 3-4시간 (반복 작업, 병렬 에이전트 활용)

### Task 4.2: 잔여 버그 4건 수정

```
Bug 1: A2-2 Playbook Node.js 탭 → 홈 이동 (High)
  원인 추정: Playbook 컴포넌트 내 탭 전환 시 router.push('/') 호출
  조사: 높은 점수(80+) 스캔으로 재현 시도
  파일: frontend/app/scan/[id]/page.tsx (Playbook 섹션)

Bug 2: A2-3 Playbook 항목 클릭 → /docs 이동 (High)
  원인 추정: 동일 컴포넌트, 항목 클릭 핸들러 잘못된 라우팅
  파일: 위와 동일

Bug 3: A1-8 Similar Tools 카테고리 기반 아님 (Medium)
  원인: 추천 알고리즘이 카테고리가 아닌 다른 기준 사용
  수정: 같은 카테고리 + 비슷한 점수 범위(±15)로 필터링
  파일: backend/app/routes/index_routes.py (similar 로직)

Bug 4: A2-7 History X축 동일 날짜 (Low)
  원인: 스캔 히스토리 데이터에 같은 날짜 중복
  수정: 날짜 기준 최신 1건만 표시, x축 포맷 정리
  파일: frontend/app/scan/[id]/page.tsx (History 차트)
```

**예상 공수**: 6-8시간

### Task 4.3: 프론트엔드에 새 데이터 표시

```
파일: frontend/app/tools/page.tsx
변경: 도구 카드에 표시 추가
  - 온라인 상태 표시등 (초록/빨강 dot)
  - pricing 배지 ("Free", "Open Source", "Paid")
  - difficulty 배지 ("Easy Setup", "Moderate", "Advanced")
  - popularity 바 (있는 경우)
  - scoring_confidence 표시 (낮으면 "Limited data" 경고)

파일: frontend/app/scan/[id]/page.tsx
변경: 스캔 결과에 추가
  - 라이브 상태 섹션 (reachable, latency, uptime)
  - source 출처 표시
  - confidence 미터
  - capabilities 리스트

파일: frontend/app/tools/page.tsx
변경: 필터에 추가
  - pricing 필터 (Free / Paid / All)
  - difficulty 필터
  - "Online only" 토글
  - source 필터 (MCP Registry / npm / GitHub / All)
```

**예상 공수**: 6-8시간

### Sprint 4 배포 체크리스트
- [ ] 모든 18개 페이지에서 모바일 햄버거 메뉴 동작 확인
- [ ] Playbook 탭 이탈 버그 재현 및 수정 확인
- [ ] 새 필터 동작 확인 (pricing, difficulty, online)
- [ ] vercel --prod 배포

---

## Sprint 5: 의미 검색 + 워크플로우 MCP (4/28-5/4)

### Task 5.1: 임베딩 기반 의미 검색

**현재 상태**: 키워드 매칭만. "파일 업로드 도구" → 결과 없음.

**작업**:
```
파일: backend/app/services/semantic_search.py (신규)

접근법: 경량 임베딩 (API 비용 최소화)
  Option A: OpenAI text-embedding-3-small ($0.02/1M tokens)
  Option B: 로컬 sentence-transformers (무료, 메모리 300MB+)
  → Render 512MB 제약 → Option A 선택

class SemanticSearch:
    def __init__(self):
        self.embeddings: dict[str, list[float]] = {}  # scan_id → vector
        self.dimension = 1536  # text-embedding-3-small

    async def build_index(self, services: list[dict]):
        """서비스 설명을 임베딩으로 변환 (시작 시 1회)"""
        # 15,000개 × 평균 50 토큰 = 750K 토큰 = $0.015
        # 배치 API 사용 (최대 2048개/요청)
        texts = [f"{s['service_name']}: {s.get('description','')}" for s in services]
        # 8배치로 나누어 임베딩
        # 결과를 embeddings-cache.npy에 저장 (numpy)

    async def search(self, query: str, top_k=20, min_score=0.3) -> list[dict]:
        """의미 검색"""
        query_vec = await self._embed(query)
        # cosine similarity 계산
        # top_k 결과 반환

    async def hybrid_search(self, query: str, top_k=20) -> list[dict]:
        """키워드 + 의미 하이브리드 (0.4 키워드 + 0.6 의미)"""
        keyword_results = self._keyword_search(query)
        semantic_results = await self.search(query)
        # RRF (Reciprocal Rank Fusion) 또는 가중 합산

파일: backend/app/routes/index_routes.py
변경: /v1/services GET에 search_mode 파라미터 추가
  - search_mode=keyword (기본, 기존 동작)
  - search_mode=semantic (의미 검색)
  - search_mode=hybrid (하이브리드)

파일: backend/app/main.py
변경: startup에서 semantic_search.build_index() 호출
      embeddings-cache.npy 존재하면 로드, 없으면 생성

환경변수: OPENAI_API_KEY (임베딩 전용)

비용: 초기 인덱스 $0.015 + 쿼리당 ~$0.00001 (무시 가능)
```

**예상 공수**: 8-10시간

### Task 5.2: 워크플로우 MCP 도구

**현재 상태**: MCP 도구 24개. 모두 단일 액션. 워크플로우 조합 없음.

**작업**:
```
파일: mcp-server/src/index.ts
변경: 신규 도구 2개 추가

1. discover_and_gate(task_description, min_rating="Moderate")
   """에이전트가 태스크를 설명하면 도구 추천 + 게이트체크 원샷"""
   Step 1: semantic_search(task_description, top_k=5)
   Step 2: 각 결과에 gate_check 실행
   Step 3: pass한 도구만 반환 (install_command 포함)

   Response:
   {
     "task": "파일을 S3에 업로드",
     "recommended_tools": [
       {
         "name": "aws-s3-mcp",
         "score": 78,
         "gate_pass": true,
         "install": "npx @aws/s3-mcp-server",
         "reason": "Direct S3 operations via MCP, high reliability"
       }
     ],
     "alternatives_checked": 5,
     "gate_pass_rate": "3/5"
   }

2. monitor_my_tools(setup_id)
   """등록된 도구셋의 실시간 상태 확인"""
   Step 1: setup에서 도구 목록 로드
   Step 2: 각 도구의 최근 probe 결과 조회
   Step 3: 이상 있는 도구 하이라이트

   Response:
   {
     "setup_id": "abc123",
     "checked_at": "2026-05-01T12:00:00Z",
     "tools": [
       {"name": "stripe-mcp", "status": "online", "latency_ms": 120, "score_change": "+2"},
       {"name": "old-api", "status": "offline", "since": "2h ago", "alternative": "new-api"}
     ],
     "alerts": ["old-api has been offline for 2 hours"]
   }

파일: mcp-server/package.json
변경: version bump (1.2.10 → 1.3.0)
```

**예상 공수**: 6-8시간

### Sprint 5 배포 체크리스트
- [ ] semantic search "file upload tool" → S3/Supabase 관련 결과 확인
- [ ] hybrid search가 keyword보다 나은 결과 반환 확인 (5개 테스트 쿼리)
- [ ] discover_and_gate MCP 도구 동작 확인
- [ ] npm publish (1.3.0)
- [ ] Render + Vercel 배포

---

## Sprint 6: 증거 엔드포인트 + 트렌드 (5/5-5/11)

### Task 6.1: Evidence 엔드포인트

**작업**:
```
파일: backend/app/routes/index_routes.py
변경: 신규 엔드포인트

GET /v1/services/{scan_id}/evidence
Response:
{
  "scan_id": "scn_abc123",
  "service_name": "stripe-mcp",
  "evidence_collected_at": "2026-05-05T12:00:00Z",
  "scoring_confidence": 82,
  "dimensions": {
    "tool_quality": {
      "score": 22,
      "max": 25,
      "evidence": {
        "tools_found": ["create_payment", "list_customers", "create_refund"],
        "description_length": 245,
        "has_input_schema": true,
        "schema_completeness": "3/3 tools have schemas"
      }
    },
    // ... 다른 차원들
  },
  "probe_evidence": {
    "last_probe": "2026-05-05T11:30:00Z",
    "reachable": true,
    "response_time_ms": 132,
    "ssl_valid": true,
    "ssl_expiry": "2027-01-15",
    "detected_features": {
      "openapi": false,
      "mcp_registry": true,
      "agents_json": false,
      "robots_txt_ai_friendly": true
    }
  },
  "external_signals": {
    "npm_weekly_downloads": 1250,
    "github_stars": 340,
    "last_release": "2026-04-20",
    "license": "MIT"
  },
  "raw_metadata_sample": {
    // 원본 레지스트리 데이터 일부 (민감 정보 제외)
  }
}

접근 제어:
  - Free: 기본 evidence (dimensions만)
  - Pro: 전체 evidence (probe + external + raw)
```

**예상 공수**: 5-6시간

### Task 6.2: Trend 엔드포인트

**작업**:
```
파일: backend/app/routes/index_routes.py
변경: 신규 엔드포인트

GET /v1/services/{scan_id}/trend?days=30
Response:
{
  "scan_id": "scn_abc123",
  "service_name": "stripe-mcp",
  "period": "30d",
  "current_score": 78,
  "score_change": +5,
  "trend": "improving",  // "improving" | "stable" | "declining"
  "history": [
    {"date": "2026-05-05", "score": 78, "rating": "Strong"},
    {"date": "2026-04-28", "score": 76, "rating": "Strong"},
    {"date": "2026-04-21", "score": 73, "rating": "Strong"},
    // ...
  ],
  "dimension_trends": {
    "tool_quality": {"current": 22, "change": +1, "trend": "stable"},
    "trust_ecosystem": {"current": 20, "change": +3, "trend": "improving"}
  },
  "probe_trend": {
    "avg_latency_ms": 145,
    "latency_change": -20,
    "uptime_30d": 99.5,
    "incidents": 1
  },
  "popularity_trend": {
    "npm_weekly": [1250, 1180, 1100, 980],  // 최근 4주
    "trend": "growing"
  }
}

데이터 소스:
  - scan_history 테이블 (기존)
  - accessibility_probes 테이블 (기존)
  - popularity-cache.json (Sprint 2에서 추가)

접근 제어:
  - Free: 7일 히스토리
  - Pro: 90일 히스토리 + 차원별 트렌드 + probe 트렌드
```

**예상 공수**: 5-6시간

### Sprint 6 배포 체크리스트
- [ ] /v1/services/{id}/evidence 응답 확인 (상위 도구 3개 테스트)
- [ ] /v1/services/{id}/trend 응답 확인 (히스토리 데이터 있는 도구)
- [ ] Free vs Pro 접근 제어 동작 확인

---

## Sprint 7: 마케팅 루프 자동화 (5/12-5/18)

### Task 7.1: 주간 인사이트 자동 리포트

**작업**:
```
파일: scripts/weekly_insight_report.py (신규)

매주 월요일 9am KST 자동 실행 → 텔레그램 발송

리포트 내용:
1. KPI 대시보드
   - 지난주 vs 이번주: API 호출, 에이전트 세션, npm 다운로드, 뱃지 노출
   - 성장률 % 표시

2. 채널 효과 순위
   - /api/admin/analytics/attribution에서 데이터 조회
   - 채널별 트래픽 + 전환율 정렬
   - "이번 주 최고 채널: smithery (+45%)"

3. 검색 쿼리 분석
   - 상위 10개 검색어
   - 결과 0건 검색어 (=커버리지 갭)
   - "에이전트가 찾지 못한 도구: database migration, image generation"

4. 도구 메이커 반응
   - 배지 PR 머지율
   - 재스캔 요청 수
   - 신규 도구 등록 수

5. 경쟁 변화
   - Smithery/Glama 신규 등록 수 (수동 입력 또는 크롤링)

6. 이번 주 실험 결과
   - 실행 중인 실험 카드 상태
   - 판정: 유지/폐기/수정

파일: .github/workflows/marketing.yml
변경: 월요일 9am KST 트리거 추가
      scripts/weekly_insight_report.py 실행
```

**예상 공수**: 5-6시간

### Task 7.2: 실험 프레임워크

**작업**:
```
파일: backend/data/experiments.json (신규)
용도: 활성 실험 추적

[
  {
    "id": "EXP-2026-05-01",
    "hypothesis": "MCP README에 3개 use case 추가하면 설치 +20%",
    "channel": "npm",
    "change": "mcp-server README.md에 use case 섹션 추가",
    "metric": "npm_weekly_downloads",
    "baseline": 1200,
    "target": 1440,
    "start_date": "2026-05-01",
    "end_date": "2026-05-08",
    "status": "active",
    "result": null,
    "verdict": null
  }
]

파일: scripts/experiment_evaluator.py (신규)
용도: 실험 종료일에 자동 평가
  - baseline 대비 metric 변화 측정
  - target 달성 여부 판정
  - 텔레그램 알림
  - experiments.json 업데이트
```

**예상 공수**: 3-4시간

### Task 7.3: 스케줄 태스크 정리 (30 → 15)

**작업**:
```
현재 30개 태스크 분석 후 통합/제거:

유지 (10개 — 핵심):
  1. clarvia-health-monitor (6h) — 플랫폼 헬스
  2. clarvia-error-guardian (10m) — 에러 감지+복구
  3. clarvia-heartbeat (5m→) — Render cold start 방지
  4. clarvia-tool-discovery (2h) — 신규 도구 수집
  5. clarvia-daily-rescan-v2 (24h) — 기존 도구 재스캔
  6. clarvia-marketing-loop (30m) — 마케팅 활동
  7. clarvia-evening-report (22:00) — 일일 리포트
  8. clarvia-morning-plan (09:00) — 일일 계획
  9. probe-scheduler (NEW, 6h) — 라이브 프로빙
  10. batch-popularity (NEW, 24h) — 채택률 수집

신규 (2개):
  11. weekly-insight (월 09:00) — 주간 인사이트
  12. experiment-evaluator (24h) — 실험 평가

제거/통합:
  - clarvia-daily-rescan (v1) → v2로 통합
  - clarvia-hourly-report → evening에 통합
  - clarvia-daily-report → evening에 통합
  - clarvia-platform-check → health-monitor에 통합
  - clarvia-platform-ops → health-monitor에 통합
  - clarvia-ops-check → health-monitor에 통합
  - clarvia-marketing-engine → marketing-loop에 통합
  - clarvia-daily-marketing → marketing-loop에 통합
  - clarvia-marketing-monitor → weekly-insight에 통합
  - clarvia-distribution-check → marketing-loop에 통합
  - clarvia-competitor-watch → weekly-insight에 통합
  - clarvia-badge-adoption → weekly-insight에 통합
  - clarvia-weekly-crawl → tool-discovery에 통합
  - clarvia-endpoint-monitor → health-monitor에 통합
  - clarvia-quality-engine → daily-rescan에 통합
  - mcp-registry-sync → tool-discovery에 통합
  - devnet-airdrop → 별도 프로젝트 이동
  - link-inbox-digest → 세션 시작 시만 확인
```

**예상 공수**: 4-5시간

### Sprint 7 배포 체크리스트
- [ ] 주간 리포트 텔레그램 수신 확인 (수동 트리거 테스트)
- [ ] experiments.json 첫 실험 등록
- [ ] 스케줄 태스크 12개로 축소 확인
- [ ] 제거된 태스크의 기능이 통합 태스크에서 커버되는지 확인

---

## Sprint 8: Pro 티어 준비 (5/19-5/25)

### Task 8.1: Pro 상품 정의 + 결제 연동

**현재 상태**: API Key 시스템 존재 (clv_ prefix). plan별 rate limit 존재. LemonSqueezy 설정 있음.

**작업**:
```
LemonSqueezy 상품 생성:
  - "Clarvia Pro" $49/month
    - Unlimited API calls
    - Semantic search
    - Full evidence endpoint
    - 90-day trend history
    - Batch gate check (100 URLs)
    - Priority support email

파일: backend/app/routes/payment_routes.py (기존)
변경: LemonSqueezy 웹훅 처리
  POST /api/webhooks/lemonsqueezy
    - subscription_created → API 키 생성 (plan: "pro")
    - subscription_updated → plan 업데이트
    - subscription_cancelled → plan → "free" 다운그레이드

파일: backend/app/services/auth_service.py
변경: Pro 키 생성 플로우
  1. 결제 성공 → create_api_key(email, plan="pro")
  2. 키 이메일 발송 (또는 대시보드 표시)
  3. 키 상태 관리 (active/suspended/expired)

파일: frontend/app/pricing/page.tsx
변경: 가격 페이지 리디자인
  - Free vs Pro 비교 테이블
  - "Get Pro" → LemonSqueezy checkout 리다이렉트
  - FAQ 섹션
```

**예상 공수**: 6-8시간

### Task 8.2: 접근 제어 적용

**현재 상태**: rate limit은 plan별로 이미 동작. 하지만 기능별 접근 제어 없음.

**작업**:
```
파일: backend/app/middleware.py
변경: 기능별 접근 제어 미들웨어

FREE_ENDPOINTS = {
    "/v1/services": {"search_mode": ["keyword"], "limit": 100},
    "/v1/services/{id}": {"fields": ["standard"]},
    "/v1/services/{id}/evidence": {"sections": ["dimensions"]},
    "/v1/services/{id}/trend": {"days": 7},
    "/v1/categories": True,
    "/v1/leaderboard": True,
    "/v1/stats": True,
    "/v1/score": True,
    "/api/scan": {"limit": "3/month"},
    "/api/badge": True,
}

PRO_ENDPOINTS = {
    "/v1/services": {"search_mode": ["keyword", "semantic", "hybrid"], "limit": None},
    "/v1/services/{id}": {"fields": ["standard", "full"]},
    "/v1/services/{id}/evidence": {"sections": "all"},
    "/v1/services/{id}/trend": {"days": 90},
    "/v1/batch-gate-check": True,  # Pro only
    # ... 나머지 Free 기능 모두 포함
}

구현:
  - 요청 시 API key → plan 조회
  - plan에 없는 기능 → 402 Payment Required + upgrade URL
  - plan에 있지만 제한 초과 → 429 + 남은 할당량

파일: backend/app/routes/index_routes.py
변경: 각 엔드포인트에서 plan 확인
  - search_mode=semantic 요청 시 plan != "pro" → 402
  - /v1/services/{id}/trend?days=30 + plan == "free" → days=7로 제한 + 헤더에 안내
```

**예상 공수**: 5-6시간

### Task 8.3: Pro 가치 증명 콘텐츠

**작업**:
```
파일: frontend/app/docs/page.tsx
변경: API 문서 업데이트
  - Pro 전용 기능 표시 (🔒 Pro 배지)
  - 각 엔드포인트에 Free vs Pro 차이 표시
  - 코드 예시 (Python, JavaScript, curl)

파일: scripts/generate_case_studies.py (신규)
용도: 점수 개선 사례 자동 생성
  - scan_history에서 점수 상승한 도구 탐색
  - before/after 비교 데이터 추출
  - 마크다운 케이스 스터디 생성
  - 목표: 5개 사례

파일: frontend/app/case-studies/ (신규 디렉토리)
용도: 점수 개선 사례 페이지
  - /case-studies — 목록
  - /case-studies/[slug] — 개별 사례
```

**예상 공수**: 5-6시간

### Sprint 8 배포 체크리스트
- [ ] LemonSqueezy 테스트 결제 → API 키 발급 확인
- [ ] Pro 키로 semantic search 가능 확인
- [ ] Free에서 semantic search → 402 확인
- [ ] pricing 페이지 디자인 확인
- [ ] 케이스 스터디 3개+ 생성

---

## Sprint 9: Pro 런칭 + 도구 메이커 접촉 (5/26-6/1)

### Task 9.1: Pro 런칭

**작업**:
```
1. LemonSqueezy 상품 활성화
2. 가격 페이지 라이브
3. API 문서 Pro 섹션 라이브
4. MCP 서버 README에 Pro 안내 추가
5. npm publish (1.4.0 — Pro 지원)

런칭 알림:
  - Smithery/Glama 프로필 업데이트
  - npm README 업데이트
  - clarvia.art 메인 페이지 배너
```

**예상 공수**: 3-4시간

### Task 9.2: 도구 메이커 아웃리치 (첫 5건)

**작업**:
```
파일: scripts/tool_maker_outreach.py (신규)
용도: 도구 메이커 자동 접촉

대상 선정 기준:
  - 점수 40-65 (개선 여지 크고, 이미 어느 정도 품질 있는)
  - GitHub repo 공개
  - 최근 6개월 업데이트
  - npm weekly downloads > 100 (관심 있을 만큼 트래픽)

접촉 방법:
  1. GitHub Issue 생성: "Improve your AEO score (currently X/100)"
     - 현재 점수 + 차원별 브레이크다운
     - 구체적 개선 3가지 (예: "MCP server 추가하면 +7점")
     - 무료 플레이북 링크
     - "Pro audit으로 더 깊은 분석 가능" CTA

  2. 배지 PR 제출 (이미 있는 기능 활용)
     - README에 AEO 배지 추가 PR
     - 점수가 높은 도구 우선 (자랑하고 싶을 테니)

목표: 주 10건 아웃리치, 2-3건 반응, 1건 유료 전환
```

**예상 공수**: 5-6시간

### Sprint 9 배포 체크리스트
- [ ] Pro 결제 플로우 E2E 확인 (실제 $49 결제 테스트)
- [ ] 첫 도구 메이커 아웃리치 5건 발송
- [ ] npm 1.4.0 publish 확인
- [ ] 런칭 후 24시간 모니터링

---

## Sprint 10: Enterprise 베타 + 웹훅 (6/2-6/8)

### Task 10.1: 웹훅 시스템

**작업**:
```
파일: backend/app/services/webhook_service.py (신규)

Supabase 테이블: webhooks
  - id: UUID
  - user_email: TEXT
  - api_key_id: TEXT (FK)
  - url: TEXT (수신 URL)
  - events: TEXT[] (구독 이벤트)
  - secret: TEXT (HMAC 서명용)
  - active: BOOL
  - created_at: TIMESTAMP

이벤트 종류:
  - tool.score_changed — 도구 점수 변동 (±5 이상)
  - tool.status_changed — 도구 온라인/오프라인 전환
  - tool.deprecated — 도구 deprecated 감지
  - tool.new_alternative — 카테고리에 새 고점수 도구 등장

웹훅 페이로드:
{
  "event": "tool.score_changed",
  "timestamp": "2026-06-05T12:00:00Z",
  "data": {
    "scan_id": "scn_abc123",
    "service_name": "stripe-mcp",
    "previous_score": 73,
    "current_score": 78,
    "change": +5,
    "dimensions_changed": ["trust_ecosystem"]
  },
  "signature": "sha256=abc..."  // HMAC-SHA256(secret, payload)
}

파일: backend/app/routes/webhook_routes.py (기존 확장)
변경:
  POST /api/webhooks — 웹훅 등록
  GET /api/webhooks — 내 웹훅 목록
  DELETE /api/webhooks/{id} — 웹훅 삭제
  POST /api/webhooks/{id}/test — 테스트 페이로드 발송

트리거 연결:
  - daily-rescan 완료 시 → 점수 변동 감지 → 웹훅 발송
  - probe 실패 시 → status_changed 웹훅 발송
```

**예상 공수**: 8-10시간

### Task 10.2: Enterprise 베타

**작업**:
```
LemonSqueezy 상품:
  - "Clarvia Enterprise" $299/month (베타 가격)
    - Pro 전체 기능
    - 웹훅 시스템
    - 커스텀 스코어링 가중치 (API)
    - SLA 99.5% (문서화)
    - 전용 이메일 지원

파일: backend/app/routes/index_routes.py
변경: 커스텀 스코어링 파라미터
  GET /v1/services?custom_weights={"agent_compatibility":40,"trust":30,"docs":20,"quality":10}
  → Enterprise 키만 사용 가능
  → 가중치 합 = 100 검증
  → 커스텀 가중치로 재계산된 점수 반환

접근 제어:
  - webhooks API → Enterprise only
  - custom_weights → Enterprise only
```

**예상 공수**: 5-6시간

---

## 운영 개선 (Sprint 전체에 걸쳐 점진적)

### Vercel 자동 배포
```
시기: Sprint 1에서 완료
작업: GitHub push → Vercel 자동 빌드/배포
방법: Vercel 대시보드에서 Git Integration 설정
      scanner/frontend 디렉토리 지정
```

### Render Heartbeat 개선
```
시기: Sprint 1에서 완료
작업: 14분 → 5분 간격
파일: clarvia-heartbeat 스케줄 태스크 수정
```

### JSONL 로그 로테이션
```
시기: Sprint 2에서 완료
파일: scripts/log_rotation.py (신규)
작업: 30일 이상 JSONL → gzip 압축 → archive/ 이동
      cron: 매주 일요일 3am
대상: analytics-*.jsonl, marketing-log.jsonl, endpoint-monitor.jsonl 등
```

### 프론트엔드 렌더링 모니터링
```
시기: Sprint 3에서 완료
파일: scripts/frontend_monitor.py (신규)
작업: 매 6시간 주요 3페이지 (/, /tools, /scan/test-url) 스냅샷
      깨짐 감지 시 텔레그램 알림
방법: headless Chrome 또는 Playwright
```

---

## 의존성 그래프

```
Sprint 1 (기반)
  ├── source 태깅 ──────────────────────┐
  ├── scoring_confidence ───────────────┤
  └── 저품질 아카이브 ──────────────────┤
                                        ▼
Sprint 2 (데이터 리치화)               Sprint 3 (라이브 프로빙)
  ├── 어트리뷰션 추적                    ├── live_prober 서비스
  ├── 응답 스키마 채우기                  └── 프로빙→점수 반영
  └── 채택률 데이터                              │
       │                                        │
       ▼                                        ▼
Sprint 4 (UI 통합) ◄────────── 새 데이터 표시
  ├── Nav 15개 적용
  └── 버그 4건
       │
       ▼
Sprint 5 (고급 기능)
  ├── 의미 검색 (임베딩)
  └── 워크플로우 MCP
       │
       ▼
Sprint 6 (투명성)
  ├── evidence 엔드포인트
  └── trend 엔드포인트
       │                    Sprint 7 (마케팅)
       │                      ├── 주간 리포트
       │                      ├── 실험 프레임워크
       │                      └── 태스크 정리
       ▼                           │
Sprint 8 (수익화 준비)  ◄──────────┘
  ├── Pro 상품 + 결제
  ├── 접근 제어
  └── 케이스 스터디
       │
       ▼
Sprint 9 (런칭)
  ├── Pro 활성화
  └── 도구 메이커 접촉
       │
       ▼
Sprint 10 (확장)
  ├── 웹훅 시스템
  └── Enterprise 베타
```

---

## 성공 기준

| 지표 | 4월 말 | 5월 말 | 6월 말 |
|------|--------|--------|--------|
| 일일 API 호출 | 500 | 2,000 | 5,000 |
| 고유 에이전트 세션/일 | 50 | 200 | 500 |
| npm 주간 다운로드 | 1,000 | 2,000 | 5,000 |
| 도구 데이터 완성도 (비-null 필드) | 60% | 80% | 90% |
| 라이브 프로빙 커버리지 | 500개 | 1,500개 | 2,000개 |
| Pro 유료 고객 | 0 | 0 | 5+ |
| MRR | $0 | $0 | $245+ |
| 점수 개선 사례 | 0 | 5 | 10 |
| 도구 메이커 반응률 | - | - | 20%+ |

---

## 리스크 & 대응

| 리스크 | 확률 | 대응 |
|--------|------|------|
| Render 512MB로 임베딩 인덱스 못 올림 | Medium | 임베딩을 파일로 저장, mmap 로드. 또는 Render 플랜 업그레이드 |
| OpenAI 임베딩 API 비용 예상 초과 | Low | 초기 인덱스 $0.015. 일 1,000쿼리 = $0.01. 무시 가능 |
| GitHub 플래그로 아웃리치 차단 | High | 이슈/PR 대신 이메일 접촉으로 전환. 플래그 해제 대기 |
| 도구 메이커 반응 없음 | Medium | 점수 40-65가 아닌 70+로 대상 변경 (이미 좋은 도구에 배지 제안) |
| Pro 전환율 0% | Medium | Free에서 semantic search 제한적 노출 (5회/일)로 맛보기 |
| Supabase free tier 한계 | Low | 현재 충분. 트래픽 10x 시 Pro 업그레이드 ($25/월) |
