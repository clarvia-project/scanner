# Clarvia 보안 감사 보고서

**감사일**: 2026-03-25
**범위**: Backend (FastAPI) + Frontend (Next.js) + Supabase 연동
**감사자**: Senior Security Engineer (12y exp)
**기준**: OWASP Top 10 2021, CWE Top 25

---

## 요약

| 심각도 | 건수 |
|--------|------|
| CRITICAL | 3 |
| HIGH | 4 |
| MEDIUM | 5 |
| LOW | 3 |
| **합계** | **15** |

---

## CRITICAL

### C-1. 프론트엔드 관리자 키 하드코딩 (CWE-798)

**파일**: `frontend/app/marketing/page.tsx:9`

```typescript
const ADMIN_KEY = "clarvia2026";
```

**공격 시나리오**: 프론트엔드 번들은 누구나 열람 가능. 브라우저 DevTools > Sources에서 `clarvia2026` 문자열을 즉시 발견할 수 있음. `/marketing?key=clarvia2026`으로 내부 KPI 대시보드에 접근 가능.

**영향**: 내부 마케팅 KPI, 스캔 통계, 카테고리 분포, 최근 스캔 대상 URL 등 비즈니스 민감 정보 전량 노출.

**수정 방법**:
```typescript
// 1. 프론트엔드에서 키를 제거
// 2. 백엔드 /v1/marketing/kpi에 API Key 인증 추가
// backend: marketing_routes.py
@router.get("/v1/marketing/kpi")
async def get_kpi(_key: ApiKeyDep):
    ...

// 3. 프론트엔드는 세션 기반 인증 또는 서버사이드 페이지로 전환
// Next.js middleware에서 쿠키 기반 인증 체크
```

---

### C-2. Supabase anon key가 .env에 평문 노출 + IDOR 위험 (CWE-200, CWE-639)

**파일**: `backend/.env:12`

```
SCANNER_SUPABASE_ANON_KEY=<REDACTED>
```

**공격 시나리오**:
1. `.env`는 `.gitignore`에 포함되어 있으나, anon key는 JWT 디코딩으로 Supabase project ref(`krumcglumpdobauujmod`) 추출 가능
2. `supabase_client.py`에서 `supabase_anon_key`로 클라이언트를 생성하므로, **RLS(Row Level Security) 미설정 시 anon key만으로 전체 테이블 접근 가능**
3. Supabase anon key는 프론트엔드에서도 사용 가능한 공개 키이므로 자체로는 비밀이 아니지만, **RLS가 비활성화되면 service_role 수준 접근**이 됨

**영향**: scans, profiles, reports, waitlist, scan_history 테이블 전체 CRUD 가능.

**수정 방법**:
```sql
-- Supabase Dashboard에서 각 테이블에 RLS 활성화
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE waitlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_history ENABLE ROW LEVEL SECURITY;

-- 백엔드에서는 service_role key 사용 (서버 전용)
-- .env: SCANNER_SUPABASE_SERVICE_KEY=eyJ...
-- config.py에 supabase_service_key 추가
-- supabase_client.py에서 service_role key로 클라이언트 생성
```

---

### C-3. 프로필 생성 API에 인증 없음 — 스팸/악성 콘텐츠 주입 (CWE-306)

**파일**: `backend/app/routes/profile_routes.py:214-215`

```python
@router.post("/profiles")
async def create_profile(req: ProfileCreateRequest):
    """Register a new service. No API key required -- open registration."""
```

**공격 시나리오**:
1. Rate limit이 `POST /api/scan`에만 적용되므로, `/v1/profiles`는 무제한 호출 가능
2. 공격자가 수만 건의 악성 프로필 등록 (피싱 URL, 악성코드 배포 URL)
3. 각 프로필은 자동 스캔(`_schedule_auto_scan`)을 트리거하여 서버 리소스 고갈 (DoS)
4. 등록된 프로필이 `/v1/services` 인덱스에 노출되어 사용자에게 악성 URL 추천 가능

**영향**: 서비스 무결성 훼손, DoS, 악성 URL 유포 플랫폼으로 악용.

**수정 방법**:
```python
# 1. 프로필 생성에 rate limit 추가
# middleware.py의 RateLimitMiddleware에 /v1/profiles POST 추가
if request.method == "POST" and (
    request.url.path.startswith("/api/scan")
    or request.url.path.startswith("/v1/profiles")
):

# 2. CAPTCHA 또는 이메일 인증 추가
# 3. 자동 스캔을 큐 기반으로 변경 (동시 실행 제한)
import asyncio
_scan_semaphore = asyncio.Semaphore(3)  # 최대 동시 3건

async def _scan():
    async with _scan_semaphore:
        ...

# 4. URL 검증 강화 (allowlist 또는 도메인 소유 확인)
```

---

## HIGH

### H-1. dev 모드 인증 우회 — 프로덕션 배포 시 위험 (CWE-287)

**파일**: `backend/app/auth.py:37-39`

```python
if not settings.admin_api_key:
    # Dev mode: no key required
    return "dev-mode"
```

**공격 시나리오**: `SCANNER_ADMIN_API_KEY` 환경변수가 설정되지 않으면, 모든 write 엔드포인트(프로필 수정, 삭제, 관리자 기능)가 인증 없이 열림. `.env` 파일에 `SCANNER_ADMIN_API_KEY`가 없음 -- **현재 프로덕션도 dev 모드일 가능성**.

**영향**: 프로필 무단 수정/삭제, 관리자 기능 접근.

**수정 방법**:
```python
async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    if not settings.admin_api_key:
        # 프로덕션에서는 절대 허용하지 않음
        logger.error("SCANNER_ADMIN_API_KEY not configured!")
        raise HTTPException(
            status_code=503,
            detail="Server misconfiguration: admin API key not set",
        )
    ...
```

---

### H-2. SSL 검증 전면 비활성화 (CWE-295)

**파일**: `backend/app/scanner.py:432` 외 50+ 곳

```python
connector = aiohttp.TCPConnector(limit=20, ssl=False)
```

모든 외부 HTTP 요청에서 `ssl=False`로 TLS 인증서 검증을 비활성화.

**공격 시나리오**: MITM(Man-in-the-Middle) 공격자가 스캔 대상과 Clarvia 서버 사이에서 응답을 변조할 수 있음. 스캔 결과를 조작하여 악성 서비스의 점수를 인위적으로 높일 수 있음.

**영향**: 스캔 결과 무결성 훼손, 잘못된 신뢰 점수 부여.

**수정 방법**:
```python
# ssl=False 제거, 기본 SSL 검증 사용
connector = aiohttp.TCPConnector(limit=20)

# 일부 자체서명 인증서 사이트를 위한 예외 처리
import ssl
ssl_context = ssl.create_default_context()
# 필요 시 특정 CA 추가
connector = aiohttp.TCPConnector(limit=20, ssl=ssl_context)
```

---

### H-3. Rate Limiter 우회 — API Key 비교 시 timing-safe하지 않음 (CWE-208)

**파일**: `backend/app/middleware.py:86`

```python
if api_key == getattr(settings, "admin_api_key", None):
    return await call_next(request)
```

**공격 시나리오**:
1. `auth.py`에서는 `secrets.compare_digest()`를 사용하지만, `middleware.py`에서는 일반 `==` 비교
2. 타이밍 사이드채널 공격으로 admin API key를 한 글자씩 추론 가능
3. 추론된 키로 rate limit 우회하여 무제한 스캔 가능

**영향**: API Key 노출, rate limit 무력화.

**수정 방법**:
```python
import secrets

if api_key and settings.admin_api_key:
    if secrets.compare_digest(api_key.encode(), settings.admin_api_key.encode()):
        return await call_next(request)
```

---

### H-4. SSRF 방어 DNS Rebinding 취약점 (CWE-918)

**파일**: `backend/app/scanner.py:50-71`

```python
def _validate_scan_url(url: str) -> None:
    ...
    try:
        resolved_ip = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(resolved_ip)
        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
            raise ValueError(...)
    except socket.gaierror:
        pass  # DNS resolution failure -- let aiohttp handle it
```

**공격 시나리오**:
1. **DNS Rebinding**: 검증 시점에는 공용 IP로 해석되지만, 실제 요청 시점에 내부 IP(127.0.0.1, 169.254.169.254)로 변경
2. **DNS 해석 실패 무시**: `socket.gaierror` 예외를 `pass`로 무시하여 검증을 건너뜀
3. 공격자가 `http://evil.com`을 제출하면, DNS가 처음엔 `1.2.3.4` → 검증 통과 → 실제 요청 시 `127.0.0.1`로 해석
4. 클라우드 메타데이터 엔드포인트(`169.254.169.254`) 접근으로 서버 자격증명 탈취

**영향**: 내부 네트워크 스캔, 클라우드 메타데이터 탈취, 내부 서비스 공격.

**수정 방법**:
```python
import socket
import ipaddress

def _validate_scan_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")

    blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if hostname.lower() in blocked_hosts:
        raise ValueError("Cannot scan localhost/loopback addresses")

    # DNS 해석 실패 시 차단
    try:
        resolved_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        raise ValueError(f"DNS resolution failed for: {hostname}")

    ip = ipaddress.ip_address(resolved_ip)
    if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
        raise ValueError(f"Cannot scan private/reserved IP range: {resolved_ip}")

    # 클라우드 메타데이터 명시 차단
    if resolved_ip in ("169.254.169.254", "fd00::c2b6:a9ff:feec:c137"):
        raise ValueError("Cannot scan cloud metadata endpoints")

    # DNS Rebinding 방어: 해석된 IP를 고정하여 사용
    return resolved_ip  # 이 IP를 실제 요청에 사용

# aiohttp 커넥터에서 해석된 IP 사용:
# connector = aiohttp.TCPConnector(
#     limit=20,
#     resolver=aiohttp.resolver.AsyncResolver(nameservers=["resolved_ip"])
# )
```

---

## MEDIUM

### M-1. 에러 응답에 내부 정보 노출 (CWE-209)

**파일**: `backend/app/main.py:189`, `backend/app/routes/profile_routes.py:496`

```python
detail=f"Scan failed: {type(e).__name__}: {str(e)[:200]}"
```

**공격 시나리오**: 의도적으로 잘못된 URL을 제출하여 내부 예외 메시지를 수집. 스택 트레이스, 라이브러리 버전, 내부 경로 등이 노출될 수 있음.

**수정 방법**:
```python
# 프로덕션에서는 일반적인 에러 메시지 반환
import os
if os.environ.get("SCANNER_ENV") == "development":
    detail = f"Scan failed: {type(e).__name__}: {str(e)[:200]}"
else:
    detail = "Scan failed. Please try again or contact support."
    logger.exception("Scan failed for URL: %s", req.url)  # 서버 로그에만 기록
```

---

### M-2. OpenAPI/Swagger 문서 프로덕션 노출 (CWE-200)

**파일**: `backend/app/main.py:33-34`

```python
docs_url="/api/docs",
redoc_url="/api/redoc",
openapi_url="/api/openapi.json",
```

**공격 시나리오**: `/api/docs`에서 전체 API 스키마, 엔드포인트 목록, 파라미터 구조를 열람 가능. 공격 표면 매핑에 활용.

**수정 방법**:
```python
import os

_is_prod = os.environ.get("SCANNER_ENV", "production") == "production"

app = FastAPI(
    ...
    docs_url=None if _is_prod else "/api/docs",
    redoc_url=None if _is_prod else "/api/redoc",
    openapi_url="/api/openapi.json",  # 공개 API이므로 유지 가능
)
```

---

### M-3. contact_email 저장 시 검증/정제 없음 (CWE-20)

**파일**: `backend/app/routes/profile_routes.py:154`

```python
contact_email: str | None = None
```

**공격 시나리오**: 이메일 필드에 XSS 페이로드(`<script>alert(1)</script>`) 또는 CRLF 인젝션 문자를 삽입. 프론트엔드에서 HTML로 렌더링 시 XSS 발생 가능.

**수정 방법**:
```python
from pydantic import EmailStr

class ProfileCreateRequest(BaseModel):
    ...
    contact_email: EmailStr | None = None
```

---

### M-4. In-Memory Rate Limiter가 다중 인스턴스에서 무력화 (CWE-799)

**파일**: `backend/app/middleware.py:44`

**공격 시나리오**: Render.com에서 여러 인스턴스 배포 시, 각 인스턴스가 독립 `_rate_store`를 가짐. 공격자가 요청마다 다른 인스턴스에 분산시키면 rate limit 우회.

**수정 방법**:
```python
# Redis 기반 rate limiter로 교체
import redis.asyncio as redis

_redis = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))

async def check_rate_limit(key: str, limit: int, window: int) -> bool:
    current = await _redis.incr(key)
    if current == 1:
        await _redis.expire(key, window)
    return current <= limit
```

---

### M-5. URL 필드 검증 부재 — 프로필 등록 시 임의 문자열 허용 (CWE-20)

**파일**: `backend/app/routes/profile_routes.py:140`

```python
url: str = Field(..., min_length=1)
```

**공격 시나리오**: `url` 필드에 `javascript:alert(1)` 또는 `file:///etc/passwd` 같은 비정상 URL 삽입. 프론트엔드에서 `<a href={url}>` 렌더링 시 XSS 또는 정보 노출.

**수정 방법**:
```python
from pydantic import HttpUrl

class ProfileCreateRequest(BaseModel):
    ...
    url: HttpUrl = Field(..., description="Service URL (https only)")
```

---

## LOW

### L-1. cache_cleanup 엔드포인트에 인증 없음 (CWE-306)

**파일**: `backend/app/main.py:247-251`

```python
@app.post("/api/cache/cleanup")
async def cache_cleanup():
    removed = cleanup_cache()
    return {"removed": removed}
```

**공격 시나리오**: 인증 없이 캐시 삭제 가능. 반복 호출로 캐시 무력화, 서버 부하 증가.

**수정 방법**:
```python
@app.post("/api/cache/cleanup")
async def cache_cleanup(_key: ApiKeyDep):
    ...
```

---

### L-2. X-Forwarded-For 스푸핑으로 rate limit 우회 가능 (CWE-290)

**파일**: `backend/app/middleware.py:48-59`

```python
_TRUSTED_PROXY_PREFIXES = ("10.", "172.16.", "192.168.", "127.")

def _get_client_ip(request: Request) -> str:
    real_ip = request.client.host if request.client else "unknown"
    if any(real_ip.startswith(p) for p in _TRUSTED_PROXY_PREFIXES) or real_ip == "::1":
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return real_ip
```

**공격 시나리오**: `172.16.x.x` 대역에서 접근 가능한 경우(같은 VPC 내부 등), `X-Forwarded-For` 헤더를 조작하여 매번 다른 IP로 위장 가능.

**수정 방법**:
```python
# Render.com 배포 시 프록시 IP를 정확히 지정
# 또는 X-Real-IP 헤더 사용 (Render에서 설정)
_TRUSTED_PROXIES = {"10.0.0.1", "10.0.0.2"}  # 실제 프록시 IP

def _get_client_ip(request: Request) -> str:
    real_ip = request.client.host if request.client else "unknown"
    if real_ip in _TRUSTED_PROXIES:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # 가장 마지막 프록시가 추가한 첫 번째 IP
            return forwarded.split(",")[0].strip()
    return real_ip
```

---

### L-3. SVG 뱃지 XSS 가능성 (CWE-79)

**파일**: `backend/app/routes/profile_routes.py:188-207`

```python
def _make_badge_svg(score: int | None) -> str:
    score_text = str(score) if score is not None else "?"
    color = _badge_color(score)
    return f"""<svg ...>{score_text}...</svg>"""
```

**공격 시나리오**: `score`는 정수이므로 현재는 안전하지만, 향후 `score_text`에 사용자 입력이 들어가면 SVG 내 스크립트 삽입 가능. `Content-Type: image/svg+xml` 응답이므로 브라우저가 SVG 내 JS를 실행함.

**수정 방법**:
```python
import html

def _make_badge_svg(score: int | None) -> str:
    score_text = html.escape(str(score)) if score is not None else "?"
    ...
```

---

## 추가 관찰 사항 (즉각 조치 불필요)

| 항목 | 상태 | 비고 |
|------|------|------|
| `.env`의 `.gitignore` 포함 여부 | OK | `.gitignore`에 `.env` 포함됨 |
| CORS 설정 | OK | 특정 도메인만 허용, `allow_credentials=False` |
| Security Headers | OK | HSTS, X-Content-Type-Options, X-Frame-Options 설정됨 |
| robots.txt | OK | `/api/`와 `/marketing` 차단됨 |
| `.well-known/` 파일들 | OK | 민감 정보 없음, 공개 API 메타데이터만 포함 |
| Validation Error 처리 | OK | 에러 상세를 500자로 제한 |
| CSP (Content-Security-Policy) | 미설정 | 추후 추가 권장 |

---

## 우선순위 조치 로드맵

| 순위 | 이슈 | 예상 공수 |
|------|------|-----------|
| 1 | C-1: 관리자 키 하드코딩 제거 | 2h |
| 2 | C-3: 프로필 생성 rate limit + 검증 | 3h |
| 3 | H-1: dev 모드 인증 우회 차단 | 30m |
| 4 | H-4: SSRF DNS Rebinding 방어 | 2h |
| 5 | C-2: Supabase RLS 활성화 | 1h |
| 6 | H-2: SSL 검증 활성화 | 1h |
| 7 | H-3: timing-safe 비교 적용 | 15m |
| 8 | M-1~M-5: 중간 우선순위 일괄 | 3h |
| 9 | L-1~L-3: 낮은 우선순위 일괄 | 1h |

**총 예상 공수**: ~14시간 (1인 기준)
