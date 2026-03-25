# Clarvia DevOps/Infrastructure Audit Report

**Date**: 2026-03-25
**Auditor**: Senior DevOps Engineer (15yr)
**Scope**: Backend (FastAPI/Render), Frontend (Next.js/Vercel), DB (Supabase), MCP Server (npm)

---

## Executive Summary

현재 Clarvia는 MVP/초기 스타트업 수준의 인프라로 운영 중입니다. 프로덕션 트래픽을 받고 있지만 엔터프라이즈급 운영에 필요한 핵심 요소들이 상당수 누락되어 있습니다. 특히 **시크릿 관리**, **모니터링 부재**, **단일 인스턴스 의존성**, **SSL 검증 비활성화**가 가장 심각한 문제입니다.

| 심각도 | 건수 |
|--------|------|
| CRITICAL | 4 |
| HIGH | 7 |
| MEDIUM | 6 |
| LOW | 3 |

---

## CRITICAL Issues

### C1. .env 파일에 실제 시크릿이 커밋됨

**심각도**: CRITICAL
**파일**: `backend/.env`

**현재 상태**: `.env` 파일에 Supabase anon key(JWT 토큰)가 평문으로 포함되어 있습니다. `.gitignore`에 `.env`가 포함되어 있지만, 파일 자체가 이미 존재하며 git history에 남아있을 가능성이 높습니다.

```
SCANNER_SUPABASE_ANON_KEY=***REMOVED***...  (실제 JWT)
```

**필요 조치**:
1. git history에서 `.env` 완전 제거 (`git filter-branch` 또는 `BFG Repo-Cleaner`)
2. Supabase anon key 즉시 로테이션
3. 로컬 개발용 `.env.example`만 커밋 (placeholder 값만 포함)
4. Render 대시보드의 Environment Variables에서만 실제 값 관리
5. CI/CD에서 `.env` 파일 존재 시 빌드 실패하도록 pre-commit hook 추가

```bash
# .env.example (이것만 커밋)
SCANNER_SUPABASE_URL=https://your-project.supabase.co
SCANNER_SUPABASE_ANON_KEY=your-anon-key-here
SCANNER_ADMIN_API_KEY=generate-a-strong-key
```

---

### C2. 전역 SSL 검증 비활성화 (ssl=False)

**심각도**: CRITICAL
**파일**: `backend/app/scanner.py:432`, 모든 checks/*.py 파일 (50+ 개소)

**현재 상태**: 아웃바운드 HTTP 요청 전체에서 `ssl=False`로 TLS 인증서 검증을 비활성화하고 있습니다. 이는 MITM(Man-in-the-Middle) 공격에 완전히 노출되는 상태입니다.

```python
# scanner.py:432
connector = aiohttp.TCPConnector(limit=20, ssl=False)
```

**필요 조치**:
1. `ssl=False` 전체 제거. 기본값(ssl=True)으로 변경
2. 자체서명 인증서 사이트 스캔이 필요하면 별도 로직으로 fallback 처리
3. 커스텀 SSL 컨텍스트로 최소 보안 기준 유지

```python
import ssl
import certifi

ssl_ctx = ssl.create_default_context(cafile=certifi.where())
connector = aiohttp.TCPConnector(limit=20, ssl=ssl_ctx)

# 스캔 대상이 자체서명 인증서인 경우에만 fallback
async def safe_request(session, url, **kwargs):
    try:
        return await session.get(url, **kwargs)
    except aiohttp.ClientSSLError:
        # TLS 실패를 스캔 결과에 반영 (감점)
        kwargs['ssl'] = False
        return await session.get(url, **kwargs)
```

---

### C3. 인메모리 캐시/레이트리밋 — 재시작 시 전부 유실

**심각도**: CRITICAL
**파일**: `backend/app/middleware.py:44`, `backend/app/scanner.py:26`

**현재 상태**:
- Rate limit 카운터: Python dict(인메모리) `_rate_store`
- 스캔 결과 캐시: Python dict(인메모리) `_scan_cache`
- Render Free 플랜은 비활성 시 인스턴스를 sleep시키므로 **모든 데이터가 주기적으로 유실됩니다**
- 멀티 워커/인스턴스 스케일아웃 시 레이트리밋이 워커별로 분리되어 무력화됨

**필요 조치**:
1. Redis 도입 (Upstash Redis Serverless 권장 - Render 무료 플랜과 호환)
2. Rate limiting을 Redis 기반으로 전환
3. 스캔 캐시도 Redis 또는 Supabase로 이전

```python
# Upstash Redis 예시 (requirements.txt에 redis 추가)
import redis
r = redis.from_url(os.environ["UPSTASH_REDIS_URL"])

# Rate limiting
def check_rate_limit(key: str, limit: int, window: int = 3600) -> bool:
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    count, _ = pipe.execute()
    return count <= limit
```

---

### C4. Render Free 플랜 — 프로덕션 운영 불가

**심각도**: CRITICAL
**파일**: `render.yaml:4`

**현재 상태**: `plan: free` — Render Free 플랜의 제약:
- 15분 비활성 시 인스턴스 sleep (cold start 30-60초)
- 월 750시간 한도
- 512MB RAM, 0.1 CPU
- 자동 스케일링 없음
- SLA 없음

**필요 조치**:
1. 최소 `starter` 플랜($7/월)으로 업그레이드 — always-on 보장
2. 프로덕션 트래픽 증가 시 `standard` 플랜 ($25/월) + autoscaling 설정

```yaml
# render.yaml
services:
  - type: web
    name: clarvia-api
    runtime: python
    plan: starter  # 최소 starter, 이상적으로는 standard
    scaling:
      minInstances: 1
      maxInstances: 3
      targetMemoryPercent: 80
      targetCPUPercent: 70
```

---

## HIGH Issues

### H1. 모니터링/알림 시스템 완전 부재

**심각도**: HIGH

**현재 상태**: 로깅은 `logging.getLogger`로 stdout에만 출력. APM, 에러 트래킹, 메트릭 수집, 알림 채널 전무.

**필요 조치**:
1. **Sentry** (에러 트래킹): 무료 플랜으로 시작
2. **Render Metrics** (기본 메트릭): CPU, 메모리, 응답시간
3. **UptimeRobot** (외부 모니터링): 무료 50개 모니터
4. **PagerDuty/OpsGenie 또는 Telegram** (알림): 장애 시 즉시 알림

```python
# requirements.txt에 추가
sentry-sdk[fastapi]>=2.0.0

# main.py 최상단
import sentry_sdk
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN", ""),
    traces_sample_rate=0.1,  # 10% 샘플링
    profiles_sample_rate=0.1,
    environment=os.environ.get("SCANNER_ENV", "production"),
)
```

---

### H2. 구조화된 로깅 부재

**심각도**: HIGH

**현재 상태**: `logging.getLogger`만 사용. JSON 포맷 없음, 요청 ID 추적 없음, 로그 레벨 동적 변경 불가.

**필요 조치**:
1. `structlog` 또는 `python-json-logger` 도입
2. 요청별 correlation ID 부여
3. 로그에 scan_id, url, duration 등 구조화된 필드 추가

```python
# structlog 설정 예시
import structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
    ],
)
```

---

### H3. health 엔드포인트가 심층 검사를 하지 않음

**심각도**: HIGH
**파일**: `backend/app/main.py:142-144`

**현재 상태**: `/health`가 단순히 `{"status": "ok"}`만 반환. DB 연결, 외부 서비스 도달 가능성 등을 검사하지 않음.

**필요 조치**:
```python
@app.get("/health")
async def health():
    checks = {"api": "ok"}

    # Supabase 연결 확인
    if _supabase_client:
        try:
            client = _supabase_client()
            # 간단한 쿼리로 연결 확인
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {type(e).__name__}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if status == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": status, "checks": checks, "version": "1.1.0"},
    )
```

---

### H4. Uvicorn workers 설정 불일치

**심각도**: HIGH
**파일**: `render.yaml:8` vs `Dockerfile:33`

**현재 상태**:
- `render.yaml`: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (worker 1개)
- `Dockerfile`: `--workers 2`
- Free 플랜 512MB RAM에서 worker 2개는 OOM 위험
- 단일 worker는 CPU-bound 작업 시 블로킹

**필요 조치**:
1. Render 배포: Gunicorn + Uvicorn worker 조합 사용
2. worker 수를 환경변수로 제어

```yaml
# render.yaml
startCommand: gunicorn app.main:app -w ${WEB_CONCURRENCY:-2} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
```

```
# requirements.txt에 추가
gunicorn>=22.0.0
```

---

### H5. 요청 body 크기 제한 없음

**심각도**: HIGH
**파일**: `backend/app/main.py`

**현재 상태**: FastAPI에 request body size limit이 설정되지 않음. 대용량 payload로 DoS 공격 가능.

**필요 조치**:
```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    MAX_BODY_SIZE = 1_048_576  # 1MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"error": "Request body too large", "max_bytes": self.MAX_BODY_SIZE},
            )
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)
```

---

### H6. 의존성 버전 고정 안 됨

**심각도**: HIGH
**파일**: `backend/requirements.txt`

**현재 상태**: `>=` 범위 지정만 되어 있어 배포마다 다른 버전이 설치될 수 있음. 재현 불가능한 빌드.

```
fastapi>=0.110.0     # 0.110 ~ 최신 아무거나 설치됨
aiohttp>=3.9.0       # breaking change 포함 가능
```

**필요 조치**:
1. `pip freeze > requirements.lock` 또는 `pip-compile`로 lock 파일 생성
2. 배포용 lock 파일과 개발용 범위 파일 분리

```
# requirements.txt (개발/범위)
fastapi>=0.115.0,<1.0
uvicorn[standard]>=0.29.0,<1.0
aiohttp>=3.9.0,<4.0

# requirements.lock (배포용 — pip-compile로 생성)
fastapi==0.115.6
uvicorn==0.32.1
aiohttp==3.11.11
```

---

### H7. SSRF 보호 우회 가능 (DNS Rebinding)

**심각도**: HIGH
**파일**: `backend/app/scanner.py:50-71`

**현재 상태**: `_validate_scan_url`이 DNS 해석 후 IP를 검증하지만, DNS rebinding 공격(첫 번째 해석은 공용 IP, 이후 해석은 사설 IP)에 취약합니다. `socket.gaierror` 시 검증을 skip하는 것도 문제.

**필요 조치**:
1. DNS 해석 결과를 고정하여 aiohttp에 전달 (TOCTOU 방지)
2. DNS 실패 시 스캔 차단 (pass가 아님)
3. IPv6 사설 주소 검증 추가

```python
def _validate_scan_url(url: str) -> str:
    """Block SSRF with DNS pinning."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")

    blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if hostname.lower() in blocked_hosts:
        raise ValueError("Cannot scan localhost/loopback addresses")

    try:
        resolved_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        raise ValueError(f"DNS resolution failed for {hostname}")

    ip = ipaddress.ip_address(resolved_ip)
    if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
        raise ValueError(f"Cannot scan private/reserved IP range: {resolved_ip}")

    return resolved_ip  # 호출자가 이 IP를 직접 사용
```

---

## MEDIUM Issues

### M1. Graceful Shutdown 미구현

**심각도**: MEDIUM
**파일**: `backend/app/main.py`

**현재 상태**: `@app.on_event("startup")`/`"shutdown"` 이벤트는 있지만, 진행 중인 스캔 작업의 graceful 종료 로직이 없음. 배포 중 진행 중인 스캔이 강제 종료됨.

**필요 조치**:
1. lifespan context manager 사용 (FastAPI 0.109+)
2. 진행 중 작업 카운터 + shutdown 시 대기

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Clarvia API starting up")
    yield
    # Shutdown
    logger.info("Shutting down — waiting for active scans...")
    # 진행 중인 스캔 완료 대기 (최대 30초)
    await asyncio.wait_for(wait_active_scans(), timeout=30)

app = FastAPI(lifespan=lifespan, ...)
```

---

### M2. 캐시 정리 수동/미자동화

**심각도**: MEDIUM
**파일**: `backend/app/main.py:247-251`

**현재 상태**: `/api/cache/cleanup` 엔드포인트가 있지만 인증 없이 누구나 호출 가능하며, 자동 정리 스케줄이 없음.

**필요 조치**:
1. 캐시 정리 엔드포인트에 admin key 인증 추가
2. 백그라운드 태스크로 주기적 정리

```python
from fastapi_utils.tasks import repeat_every  # 또는 asyncio.create_task

@app.on_event("startup")
@repeat_every(seconds=3600)
async def auto_cleanup():
    removed_cache = cleanup_cache()
    removed_rate = cleanup_rate_store()
    logger.info("Auto cleanup: cache=%d, rate=%d", removed_cache, removed_rate)
```

---

### M3. CSP에 unsafe-inline/unsafe-eval 허용

**심각도**: MEDIUM
**파일**: `frontend/vercel.json:13`

**현재 상태**: `script-src 'self' 'unsafe-inline' 'unsafe-eval'` — XSS 공격 벡터가 열려 있음.

**필요 조치**:
1. `unsafe-inline` -> nonce 기반으로 전환
2. `unsafe-eval` 제거 (Next.js 빌드 설정 조정 필요)

```json
{
  "key": "Content-Security-Policy",
  "value": "default-src 'self'; script-src 'self' 'nonce-{{nonce}}'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://clarvia-api.onrender.com https://*.vercel.app; frame-ancestors 'none'"
}
```

---

### M4. Supabase 백업/복구 전략 부재

**심각도**: MEDIUM

**현재 상태**: Supabase Free 플랜 사용 시 자동 백업은 있으나 7일 보존. Point-in-time recovery 없음. 데이터 복구 전략 미수립.

**필요 조치**:
1. Supabase Pro 플랜($25/월) — 30일 백업 + PITR
2. 주간 pg_dump 스크립트를 cron으로 외부 스토리지(S3/R2)에 저장
3. 복구 절차 문서화 및 분기별 복구 테스트

---

### M5. CI/CD 파이프라인 부재

**심각도**: MEDIUM

**현재 상태**: `autoDeploy: true`로 git push 시 자동 배포되지만:
- 테스트 실행 없음
- 린트/타입 체크 없음
- 스테이징 환경 없음
- 롤백 자동화 없음

**필요 조치**:
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest --tb=short
      - run: cd backend && python -m mypy app/ --ignore-missing-imports

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/main'
    # Render preview 환경 자동 배포

  deploy-production:
    needs: deploy-staging
    if: startsWith(github.ref, 'refs/tags/v')
    # 태그 기반 프로덕션 배포
```

---

### M6. 에러 응답에 내부 정보 노출

**심각도**: MEDIUM
**파일**: `backend/app/main.py:189`

**현재 상태**: 500 에러에서 exception 타입과 메시지를 그대로 클라이언트에 반환.

```python
detail=f"Scan failed: {type(e).__name__}: {str(e)[:200]}"
```

**필요 조치**:
```python
# 프로덕션에서는 내부 에러 숨김
if os.environ.get("SCANNER_ENV") == "production":
    raise HTTPException(status_code=500, detail="Internal server error")
else:
    raise HTTPException(status_code=500, detail=f"Scan failed: {type(e).__name__}: {str(e)[:200]}")
```

---

## LOW Issues

### L1. Dockerfile의 data/ 디렉토리 COPY

**심각도**: LOW
**파일**: `backend/Dockerfile:19`

**현재 상태**: `COPY data/ ./data/`가 있지만 Render는 Dockerfile을 사용하지 않고 직접 빌드. Docker 빌드 시 data/ 없으면 실패.

**필요 조치**: `.dockerignore` 추가, 빌드 시 data 존재 여부 확인 또는 조건부 COPY.

---

### L2. API 문서가 프로덕션에 공개

**심각도**: LOW
**파일**: `backend/app/main.py:33-34`

**현재 상태**: `/api/docs`, `/api/redoc`, `/api/openapi.json`이 인증 없이 공개.

**필요 조치**: 프로덕션에서는 비활성화하거나 admin 인증 추가.

```python
docs_url = "/api/docs" if os.environ.get("SCANNER_ENV") != "production" else None
redoc_url = "/api/redoc" if os.environ.get("SCANNER_ENV") != "production" else None
```

---

### L3. User-Agent에 잘못된 도메인

**심각도**: LOW
**파일**: `backend/app/scanner.py:427`

**현재 상태**: `User-Agent: ClarviaScannerBot/1.0 (+https://clarvia.io/bot)` — 실제 도메인은 `clarvia.art`.

**필요 조치**:
```python
"User-Agent": "ClarviaScannerBot/1.0 (+https://clarvia.art/bot)",
```

---

## 즉시 실행 우선순위 (Action Items)

| 순위 | 항목 | 예상 소요 | 비용 |
|------|------|-----------|------|
| 1 | C1: .env 시크릿 제거 + key 로테이션 | 1시간 | 무료 |
| 2 | C4: Render Starter 플랜 업그레이드 | 10분 | $7/월 |
| 3 | C2: ssl=False 제거 | 2시간 | 무료 |
| 4 | H1: Sentry 연동 | 30분 | 무료 (5K events/월) |
| 5 | H6: requirements.lock 생성 | 15분 | 무료 |
| 6 | C3: Upstash Redis 도입 | 2시간 | 무료 (10K cmd/일) |
| 7 | H5: Request body size limit | 15분 | 무료 |
| 8 | H7: SSRF DNS pinning | 1시간 | 무료 |
| 9 | H3: Deep health check | 30분 | 무료 |
| 10 | M5: GitHub Actions CI | 2시간 | 무료 (2000분/월) |

---

## 아키텍처 개선 로드맵

### Phase 1: 즉시 (이번 주)
- 시크릿 정리 (C1)
- Render 플랜 업그레이드 (C4)
- SSL 검증 활성화 (C2)
- Sentry 연동 (H1)

### Phase 2: 단기 (2주 내)
- Redis 도입 (C3)
- CI/CD 파이프라인 (M5)
- 의존성 버전 고정 (H6)
- SSRF 강화 (H7)

### Phase 3: 중기 (1개월 내)
- 구조화된 로깅 (H2)
- Supabase 백업 전략 (M4)
- CSP 강화 (M3)
- 스테이징 환경 구축
