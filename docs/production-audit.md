# Clarvia Production Audit Report

**Date**: 2026-03-25
**Auditor**: Claude Code (Automated)
**Scope**: Frontend (Next.js/Vercel), Backend (FastAPI/Render), MCP Server (npm), Data, Infra

---

## Summary

| Category | OK | WARNING | CRITICAL | TODO |
|----------|---:|--------:|---------:|-----:|
| Database | 2 | 2 | 1 | 1 |
| Environment Variables | 3 | 2 | 1 | 2 |
| Deployment | 5 | 1 | 0 | 1 |
| Security | 5 | 2 | 1 | 1 |
| Dependencies | 2 | 2 | 0 | 1 |
| Monitoring/Logging | 2 | 1 | 2 | 2 |
| Data Files | 2 | 2 | 0 | 1 |
| API Stability | 4 | 1 | 0 | 0 |
| Domain/DNS | 2 | 0 | 0 | 2 |
| CI/CD | 3 | 1 | 0 | 1 |
| **Total** | **30** | **14** | **5** | **12** |

---

## 1. Database (Supabase)

### Connection
- ✅ OK — Supabase URL/anon key configured in `backend/.env`
- ✅ OK — Graceful degradation: Supabase 미연결 시 in-memory 모드로 동작 (`supabase_client.py`)

### Tables: Required vs Schema
`backend/schema.sql`에 정의된 6개 테이블:

| Table | Purpose | Status |
|-------|---------|--------|
| `scans` | Scan results | ✅ OK |
| `reports` | Paid report records | ✅ OK |
| `waitlist` | Email collection | ✅ OK |
| `scan_history` | Time-series trend data | ✅ OK |
| `tracked_urls` | Periodic auto-rescan URLs | ✅ OK |
| `accessibility_probes` | AI agent accessibility tests | ✅ OK |

- ⚠️ WARNING — `api_keys` 테이블이 `auth_service.py`에서 사용되지만 `schema.sql`에 정의 없음
- ❌ CRITICAL — **schema.sql이 실제 Supabase에 적용되었는지 확인 불가**. Supabase SQL Editor에서 직접 확인 필요

### RLS Policies
- ⚠️ WARNING — RLS 활성화되었으나 **모든 정책이 `USING (true)`**로 설정됨. Anon key로 누구나 모든 데이터 읽기/쓰기 가능. 프로덕션에서는 service_role key를 사용하거나 RLS 정책을 강화해야 함

### Backup
- 📋 TODO — Supabase 자동 백업 설정 확인 필요 (Pro plan: 일일 백업, Free plan: 백업 없음)

---

## 2. Environment Variables

### Backend (`backend/.env`)
| Variable | Status | Notes |
|----------|--------|-------|
| `SCANNER_HOST` | ✅ OK | `0.0.0.0` |
| `SCANNER_PORT` | ✅ OK | `8003` (로컬) |
| `SCANNER_FRONTEND_URL` | ✅ OK | |
| `SCANNER_SUPABASE_URL` | ✅ OK | 실제 값 설정됨 |
| `SCANNER_SUPABASE_ANON_KEY` | ✅ OK | 실제 값 설정됨 |
| `SCANNER_STRIPE_SECRET_KEY` | ⚠️ WARNING | `sk_test_placeholder` — 실 결제 전 교체 필요 |
| `SCANNER_STRIPE_WEBHOOK_SECRET` | ⚠️ WARNING | `whsec_placeholder` |
| `SCANNER_STRIPE_PRICE_ID` | ⚠️ WARNING | 빈 값 |
| `SCANNER_CORS_ORIGINS` | ✅ OK | 프로덕션 도메인 포함 |
| `SCANNER_ADMIN_API_KEY` | ❌ CRITICAL | **`.env`에 누락** — `render.yaml`에는 정의됨. 로컬에서 admin 엔드포인트가 인증 없이 열려있음 |
| `SCANNER_LEMONSQUEEZY_*` | 📋 TODO | Lemon Squeezy 설정이 `config.py`에 있지만 `.env`/`.env.example`에 없음 |

### Frontend
| Variable | Status | Notes |
|----------|--------|-------|
| `NEXT_PUBLIC_API_URL` | ✅ OK | `lib/api.ts`에서 참조, fallback `localhost:8000` |

### Render 배포 시 필요 (render.yaml 기준)
```
PYTHON_VERSION=3.12.0
SCANNER_ENV=production
SCANNER_FRONTEND_URL=https://clarvia.art
SCANNER_CORS_ORIGINS=[...]
SCANNER_SUPABASE_URL         ← 수동 입력 필요 (sync: false)
SCANNER_SUPABASE_ANON_KEY    ← 수동 입력 필요
SCANNER_STRIPE_SECRET_KEY    ← 수동 입력 필요
SCANNER_STRIPE_WEBHOOK_SECRET ← 수동 입력 필요
SCANNER_STRIPE_PRICE_ID      ← 수동 입력 필요
SCANNER_ADMIN_API_KEY         ← 수동 입력 필요
```

### Vercel 배포 시 필요
```
NEXT_PUBLIC_API_URL=https://clarvia-api.onrender.com (또는 https://api.clarvia.art)
```

### 누락된 환경변수
- 📋 TODO — `SCANNER_LEMONSQUEEZY_STORE_ID`, `SCANNER_LEMONSQUEEZY_VARIANT_ID`, `SCANNER_LEMONSQUEEZY_WEBHOOK_SECRET` 를 `.env.example`에 추가

---

## 3. Deployment

### Vercel (Frontend)
- ✅ OK — `frontend/vercel.json` 존재, security headers 설정 (HSTS, CSP, X-Frame-Options 등)
- ✅ OK — `buildCommand`, `installCommand` 명시
- ✅ OK — CSP에 `connect-src`로 API 도메인 허용
- ⚠️ WARNING — 루트의 `vercel.json`은 `experimentalServices` 사용 (monorepo 실험 기능). **프론트엔드는 별도 Vercel 프로젝트**로 `frontend/vercel.json`이 적용되어야 함

### Render (Backend)
- ✅ OK — `render.yaml` 존재, Free plan, Oregon region
- ✅ OK — `healthCheckPath: /health` 설정
- ✅ OK — `autoDeploy: true`

### Docker
- ✅ OK — `backend/Dockerfile` 존재, non-root user, healthcheck 포함
- 📋 TODO — `frontend/Dockerfile` 존재하지만 Vercel 사용 시 불필요. Docker 배포 시에만 필요

### Build Scripts
- ✅ OK — `backend/Procfile`: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- ✅ OK — `frontend/package.json`: `npm run build` → `next build`

---

## 4. Security

### API Key Management
- ✅ OK — 하드코딩된 실제 API 키 없음 (Stripe placeholder만 `.env`에 존재)
- ✅ OK — `.gitignore`에 `.env` 포함
- ⚠️ WARNING — `backend/.env`에 실제 Supabase anon key가 있고, Git에서 추적되지 않지만 로컬에 평문 저장

### CORS
- ✅ OK — 화이트리스트 방식, 프로덕션 도메인 명시적 허용
- ✅ OK — `allow_credentials=False`

### Rate Limiting
- ✅ OK — `RateLimitMiddleware` 구현
  - IP당 10 scans/hour (free)
  - API key당 100 scans/hour
  - POST /api/scan 에만 적용
- ⚠️ WARNING — **인메모리 rate store** — Render free tier는 재시작 시 초기화됨. Redis 기반으로 전환 고려

### Security Headers
- ✅ OK — Backend `SecurityHeadersMiddleware`: X-Content-Type-Options, X-Frame-Options, HSTS, X-XSS-Protection
- ✅ OK — Frontend `vercel.json`: CSP, Permissions-Policy, Referrer-Policy 등

### Marketing Dashboard Access
- ❌ CRITICAL — `/v1/marketing/kpi` 엔드포인트에 **인증 없음**. 누구나 내부 KPI 데이터 조회 가능. `ApiKeyDep` 적용 필요

### Sensitive Data Exposure
- ✅ OK — `.env` 파일이 `.gitignore`에 포함
- ✅ OK — `robots.txt`에서 `/api/`와 `/marketing` 경로 차단

---

## 5. Dependencies

### Backend (`requirements.txt`)
- ✅ OK — 핵심 패키지 명시됨
- ⚠️ WARNING — **버전 핀닝이 최소 버전만 지정** (`>=`). 프로덕션에서는 `==`으로 정확한 버전 고정 권장
- ⚠️ WARNING — 개발/테스트 의존성 (`pytest`, `httpx`, `ruff`)이 `requirements.txt`에 없고 CI에서만 설치. `requirements-dev.txt` 분리 권장
- 📋 TODO — `pip audit` 또는 Dependabot으로 취약점 스캔 설정 필요

### Frontend (`package.json`)
- ✅ OK — Next.js 16.2.1, React 19.2.4 — 최신 버전
- ✅ OK — `package-lock.json` 존재, 재현 가능한 빌드

### Packages (Known Risks)
| Package | Version | Notes |
|---------|---------|-------|
| `fastapi` | >=0.110.0 | OK |
| `uvicorn` | >=0.29.0 | OK |
| `supabase` | >=2.0.0 | OK |
| `stripe` | >=8.0.0 | OK |
| `next` | 16.2.1 | 최신 |
| `react` | 19.2.4 | 최신 |

---

## 6. Monitoring / Logging

### Error Monitoring
- ❌ CRITICAL — **Sentry 등 에러 모니터링 미설정**. 프로덕션 에러를 실시간으로 추적할 수 없음

### Logging
- ✅ OK — Python `logging` 모듈 사용, 주요 에러에 `logger.error()` 적용
- ⚠️ WARNING — 구조화된 로깅(JSON format) 미적용. Render 로그 검색 시 불편

### Health Check
- ✅ OK — `GET /health` 엔드포인트 존재, `render.yaml`에 `healthCheckPath` 설정

### Uptime Monitoring
- ❌ CRITICAL — **외부 업타임 모니터링 미설정**. UptimeRobot, Better Stack 등으로 `/health` 모니터링 필요
- 📋 TODO — UptimeRobot Free (5분 간격) 또는 Better Stack 설정
- 📋 TODO — Render free tier는 15분 비활성 시 sleep. 업타임 모니터링이 keep-alive 역할도 함

---

## 7. Data Files

### `prebuilt-scans.json`
- ✅ OK — 1.1MB, Dockerfile의 `COPY data/ ./data/`로 배포에 포함
- ⚠️ WARNING — `backend/data/`에 11MB 데이터 (mcp-registry-all.json 5.4MB 포함). Render free tier 512MB RAM 제한 고려 필요

### `data/` (Root)
- ⚠️ WARNING — 루트 `data/` 디렉토리에 16MB+ 데이터 (로그, PID, 스캔 결과 등). **배포에 포함되면 안 되는 운영 데이터**가 혼재. `.gitignore`에 `data/*.log`, `data/*.pid` 추가 권장

### Static Assets
- ✅ OK — `frontend/public/` 정상: favicon, apple-touch-icon, logos, sitemap.xml, robots.txt, llms.txt
- 📋 TODO — OG 이미지 (`og-image.png`) 존재 여부 확인 필요 (SEO 중요)

---

## 8. API Stability

### Error Handling
- ✅ OK — RFC 7807 스타일 에러 응답 구현
- ✅ OK — `RequestValidationError` 핸들러 존재
- ✅ OK — Supabase 연결 실패 시 graceful degradation

### Timeout
- ✅ OK — `SCANNER_HTTP_TIMEOUT=10.0` (HTTP probing 타임아웃)
- ⚠️ WARNING — 전체 스캔 타임아웃이 명시적으로 없음. 복잡한 URL 스캔 시 Render 30초 타임아웃에 걸릴 가능성

### Cache
- ✅ OK — `SCANNER_CACHE_TTL_SECONDS=86400` (24시간 캐시)
- ✅ OK — API 응답에 `Cache-Control: no-store` 헤더

### Rate Limiting
- ✅ OK — 위 Section 4 참조

---

## 9. Domain / DNS

### clarvia.art
- ✅ OK — sitemap.xml, robots.txt에서 `clarvia.art` 사용
- ✅ OK — CORS에 `clarvia.art`, `www.clarvia.art` 포함
- 📋 TODO — **실제 도메인 등록/DNS 설정 확인 필요** (Vercel/Render custom domain 연결)

### SSL
- ✅ OK — Vercel, Render 모두 자동 SSL 제공
- ✅ OK — HSTS 헤더 설정됨 (`max-age=31536000; includeSubDomains`)

### API Subdomain
- 📋 TODO — `api.clarvia.art` → Render 배포 연결 여부 확인. CI에서 `NEXT_PUBLIC_API_URL: https://api.clarvia.art` 사용 중이지만, CSP에서는 `clarvia-api.onrender.com`만 허용. **불일치 가능성**

---

## 10. CI/CD

### GitHub Actions
- ✅ OK — `.github/workflows/ci.yml`: backend lint+test, frontend build, mcp-server build
- ✅ OK — `.github/workflows/clarvia-score.yml`: PR 시 URL 변경 감지 후 자동 스캔
- ✅ OK — Python 3.12, Node 20 사용

### Test Coverage
- ⚠️ WARNING — 테스트 파일 1개 (`test_e2e.py`, 16KB). 유닛 테스트 부족, 커버리지 측정 미설정

### Linting
- ✅ OK — `ruff` 사용 (CI에서)

### Auto-Deploy
- 📋 TODO — Render `autoDeploy: true` 설정됨. main 브랜치 push 시 자동 배포 확인 필요

---

## Priority Action Items

### CRITICAL (즉시 수정)
1. **Marketing KPI 엔드포인트 인증** — `/v1/marketing/kpi`에 `ApiKeyDep` 추가
2. **SCANNER_ADMIN_API_KEY** — Render 환경에 반드시 설정, 로컬 `.env`에도 추가
3. **Sentry 에러 모니터링** — `pip install sentry-sdk[fastapi]` + DSN 설정
4. **업타임 모니터링** — UptimeRobot 또는 Better Stack에 `/health` 등록
5. **Supabase schema 적용 확인** — `api_keys` 테이블 포함 여부, RLS 정책 검토

### WARNING (1주 내 개선)
1. Rate limit store를 Redis로 전환 (Render 재시작 시 초기화 방지)
2. `requirements.txt` 버전 핀닝 (`>=` → `==`)
3. RLS 정책 강화 (anon 사용자 쓰기 제한)
4. 구조화된 로깅 (JSON format) 도입
5. `api.clarvia.art` vs `clarvia-api.onrender.com` CSP 불일치 해소
6. 루트 `data/` 디렉토리 `.gitignore` 보강

### TODO (배포 전)
1. Render 환경변수 수동 설정 (Supabase, Stripe, Admin key)
2. Vercel 환경변수 설정 (`NEXT_PUBLIC_API_URL`)
3. 도메인 DNS 설정 확인 (clarvia.art → Vercel, api.clarvia.art → Render)
4. Lemon Squeezy 환경변수를 `.env.example`에 추가
5. Dependabot 또는 `pip audit` 설정
6. Supabase 백업 전략 확인 (Plan tier에 따라)
7. OG 이미지 존재 확인
