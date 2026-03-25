# Clarvia Backend Audit Report

**Date**: 2026-03-25
**Auditor**: Senior Backend Engineer (13yr exp)
**Scope**: FastAPI backend — architecture, code quality, scalability, security

---

## Executive Summary

Clarvia backend는 FastAPI 기반 모놀리식 구조로 2,908줄 main.py가 핵심 병목입니다. 인메모리 캐시가 4곳에 분산되어 메모리 누수 위험이 있고, Supabase + JSON 이중 저장이 데이터 정합성 문제를 일으킬 수 있습니다. 전체 코드베이스는 약 12,100줄입니다.

**총 이슈: 23건** — CRITICAL 4 / HIGH 8 / MEDIUM 7 / LOW 4

---

## CRITICAL Issues

### C1. main.py 2,908줄 모놀리스 — God Object

**심각도**: CRITICAL
**파일**: `app/main.py`

**현재 상태**: 52개 함수/엔드포인트가 단일 파일에 존재. FIX_TEMPLATES dict만 1,000줄 이상 차지. mcp-scan, authenticated-scan, fix-code-gen, playbook, traffic monitoring, scan history가 모두 main.py에 인라인.

**문제점**:
- 하나의 엔드포인트 수정이 전체 파일 충돌 유발
- 테스트 격리 불가능 — 모든 import가 app 초기화 시 실행
- FIX_TEMPLATES (코드 템플릿 800줄+)은 데이터이지 로직이 아님
- `import json`, `import aiohttp`가 함수 내부에서 반복 임포트 (line 265, 323, 363, 504, 564, 600, 658-660)

**수정 방법**:
```
main.py (앱 초기화 + 라우터 마운트만)
routes/
  scan_routes.py       ← /api/scan, /api/scan/{id}, /api/scan/authenticated
  mcp_scan_routes.py   ← /api/v1/mcp-scan
  fix_routes.py        ← /api/v1/fix, /api/v1/playbook
  traffic_routes.py    ← /api/v1/traffic/*
  history_routes.py    ← /api/v1/history
  public_api_routes.py ← /api/v1/score, leaderboard, compare, methodology
data/
  fix_templates.json   ← FIX_TEMPLATES를 JSON으로 분리
```

### C2. 인메모리 캐시 4곳 분산 — 메모리 폭발 + OOM 위험

**심각도**: CRITICAL
**파일**: `scanner.py`, `middleware.py`, `checks/agent_compatibility.py`, `services/supabase_client.py`

**현재 상태**:
| 위치 | 변수명 | TTL | 정리 메커니즘 | 크기 제한 |
|------|--------|-----|---------------|-----------|
| `scanner.py:26` | `_scan_cache` | 24h | 수동 cleanup_cache() | **없음** |
| `middleware.py:44` | `_rate_store` | 2h | 수동 cleanup_rate_store() | **없음** |
| `agent_compatibility.py:36` | `_registry_cache` | 1h | lazy eviction | **없음** |
| `supabase_client.py:186` | `_history_fallback` | 없음 | URL당 100건 cap | **URL 수 무제한** |

**문제점**:
- cleanup_cache()는 /api/cache/cleanup POST로만 호출 가능 — 자동 실행 없음
- 24시간 TTL + 크기 제한 없음 = 스캔 요청이 많으면 메모리 무한 성장
- _history_fallback는 URL당 100건이지만 URL 자체 수가 무제한
- Render.com 512MB 인스턴스에서 OOM crash 가능

**수정 방법**:
1. `cachetools.TTLCache(maxsize=1000, ttl=86400)` 사용하여 크기 제한 추가
2. 또는 LRU 기반: `functools.lru_cache` 대신 `cachetools.LRUCache`
3. 주기적 cleanup을 `BackgroundTasks` 또는 `asyncio.create_task()`로 자동화
4. 장기적으로 Redis로 이관 (멀티 인스턴스 배포 시 필수)

```python
# scanner.py — 개선안
from cachetools import TTLCache
_scan_cache: TTLCache = TTLCache(maxsize=2000, ttl=86400)
```

### C3. tool_scorer.py 데드코드 — return 이후 실행 안 되는 코드

**심각도**: CRITICAL
**파일**: `app/tool_scorer.py`, lines 297-313

**현재 상태**: `normalize_tool()` 함수에서 line 283에 `return` 문이 있고, line 299부터 auto-extract keywords 로직이 있으나 **절대 실행되지 않음**.

```python
    return {  # line 283
        "scan_id": scan_id,
        ...
    }

    # Auto-extract keywords from description when keywords list is empty
    if not result["tags"] and desc:  # line 300 — DEAD CODE
        ...
    return result  # line 313 — DEAD CODE
```

**문제점**: 12,800+ 도구 중 태그 없는 도구들이 빈 태그로 인덱싱되어 TF-IDF 추천 품질 저하

**수정 방법**: line 283의 return을 `result = {` 로 변경하고 line 313의 return만 남기기

### C4. Supabase 클라이언트 동기 호출을 async 함수에서 사용

**심각도**: CRITICAL
**파일**: `app/services/supabase_client.py`

**현재 상태**: `save_scan()`, `get_scan_from_db()` 등이 모두 `async def`이지만 내부에서 `client.table().execute()`는 **동기 HTTP 호출** (supabase-py는 동기 클라이언트). 이벤트 루프를 블로킹.

**문제점**:
- 모든 Supabase 호출이 이벤트 루프를 블로킹하여 동시 요청 처리 불가
- 스캔 요청 중 Supabase 저장이 느리면 다른 요청도 대기

**수정 방법**:
```python
# Option 1: asyncio.to_thread로 감싸기
import asyncio
result = await asyncio.to_thread(
    lambda: client.table("scans").upsert(data, on_conflict="scan_id").execute()
)

# Option 2: supabase async client 사용 (supabase-py 2.x)
from supabase._async.client import create_client as create_async_client
```

---

## HIGH Issues

### H1. JSON 파일 + Supabase 이중 저장 — 데이터 정합성 불일치

**심각도**: HIGH
**파일**: `routes/profile_routes.py`

**현재 상태**: `_save_profiles()`가 JSON 파일 먼저 저장, Supabase에 각 프로필을 개별 upsert. 예외 시 `pass`로 무시 (line 103).

**문제점**:
- JSON 성공 + Supabase 실패 = 재시작 시 Supabase 데이터 유실
- Supabase 성공 + JSON 실패 = 로컬 데이터 유실
- `_load_profiles()`에서 "파일에 없는 프로필만 Supabase에서 추가"하므로 파일이 truth source인데, 파일 쓰기 실패 시 데이터 유실
- race condition: 동시 프로필 생성 시 JSON 파일 덮어쓰기

**수정 방법**:
1. Supabase를 단일 truth source로 지정
2. JSON은 read-only fallback (Supabase 미연결 시)
3. 파일 쓰기 시 atomic write (tempfile + rename)
4. 개별 upsert 대신 batch upsert

### H2. SSRF 보호 불완전 — DNS rebinding 공격 가능

**심각도**: HIGH
**파일**: `app/scanner.py`, lines 50-71

**현재 상태**: `_validate_scan_url()`이 DNS 해석 후 IP 검증하지만, aiohttp 요청 시 재해석 가능 (TOCTOU).

**문제점**:
- DNS rebinding: 검증 시점엔 공개 IP, 실제 요청 시 내부 IP로 변경 가능
- `ssl=False`로 TLS 검증 비활성화 (scanner.py line 432)
- `socket.gaierror` 시 `pass`로 검증 건너뜀

**수정 방법**:
1. aiohttp connector에서 `resolver` 커스텀으로 내부 IP 차단
2. `ssl=False` 제거하고 별도 SSL context 사용
3. DNS 해석 실패 시 ValueError raise

```python
class SafeResolver(aiohttp.DefaultResolver):
    async def resolve(self, host, port=0, family=0):
        results = await super().resolve(host, port, family)
        for r in results:
            ip = ipaddress.ip_address(r['host'])
            if ip.is_private or ip.is_reserved or ip.is_loopback:
                raise ValueError(f"SSRF blocked: {host} -> {r['host']}")
        return results
```

### H3. 12,800+ 도구 TF-IDF 인덱스 메모리 사용량

**심각도**: HIGH
**파일**: `app/recommender.py`

**현재 상태**: `TfidfVectorizer(max_features=15000, ngram_range=(1,2))`로 12,800+ 문서 인덱싱. 예상 메모리: sparse matrix ~50-80MB + vectorizer vocabulary ~10MB.

**문제점**:
- 서버 시작 시 모든 JSON 파일 로드 + TF-IDF fit_transform → cold start 지연
- ngram_range=(1,2)는 vocabulary를 2-3배 증가시킴
- 싱글턴 `_engine`이 프로세스 수명 동안 메모리 점유
- index_routes._load_collected()가 all-agent-tools.json (수십 MB) 전체를 메모리에 로드

**수정 방법**:
1. `max_features=10000`으로 감소 (추천 품질 영향 미미)
2. lazy loading: 첫 추천 요청 시 인덱스 빌드 (현재도 부분적으로 적용)
3. 장기: Qdrant/ChromaDB 같은 벡터 DB로 이관
4. 도구 데이터를 JSON 대신 SQLite로 저장하여 메모리 절감

### H4. asyncio.gather 에러 전파 — 하나의 체크 실패가 전체 스캔 실패

**심각도**: HIGH
**파일**: `app/scanner.py`, line 487

**현재 상태**:
```python
all_results = await asyncio.gather(*api_tasks, ac_task, ts_task, oc_task)
```
`return_exceptions=True` 미사용.

**문제점**: 5개 체크 중 하나라도 예외 발생하면 전체 스캔 실패. 예를 들어 onchain_bonus 체크가 실패해도 나머지 4개의 유효한 결과가 버려짐.

**수정 방법**:
```python
all_results = await asyncio.gather(
    *api_tasks, ac_task, ts_task, oc_task,
    return_exceptions=True,
)
# 각 결과를 검사하여 예외 시 기본값 사용
for i, r in enumerate(all_results):
    if isinstance(r, Exception):
        logger.warning("Check %d failed: %s", i, r)
        all_results[i] = {"score": 0, "sub_factors": {}, "max": 25}
```

### H5. 레이트 리미터 defaultdict 무한 성장

**심각도**: HIGH
**파일**: `app/middleware.py`, line 44

**현재 상태**: `_rate_store: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)` — 모든 고유 IP/API 키가 영구 저장.

**문제점**:
- DDoS 공격 시 수백만 개의 고유 IP 키가 생성되어 메모리 폭발
- cleanup_rate_store()는 자동 호출되지 않음
- defaultdict이므로 존재하지 않는 키 조회만으로도 엔트리 생성

**수정 방법**:
```python
from cachetools import TTLCache
_rate_store: TTLCache = TTLCache(maxsize=50000, ttl=WINDOW_SECONDS * 2)
```

### H6. 인증 스캔에서 API 키 메모리 잔류

**심각도**: HIGH
**파일**: `app/main.py`, lines 497-642

**현재 상태**: authenticated_scan에서 사용자의 API 키를 `session_headers`에 넣어 aiohttp 세션에 전달. 세션 종료 후에도 Python 가비지 컬렉터가 정리할 때까지 메모리에 잔류.

**문제점**: 민감한 API 키가 메모리에 불확정 시간 동안 존재. 코어 덤프 시 노출 위험.

**수정 방법**:
- 사용 후 dict에서 명시적으로 삭제
- `del api_key, auth_headers` 추가
- 장기: 키를 메모리에 저장하지 않고 프록시 패턴 사용

### H7. prebuilt-scans.json을 매 요청마다 파일 I/O

**심각도**: HIGH
**파일**: `app/main.py`, lines 277-294, 326-354, 372-377

**현재 상태**: `/api/v1/score`, `/api/v1/leaderboard`, `/api/v1/compare`가 매 요청마다 `Path.exists()` + `open()` + `json.load()` 실행.

**문제점**:
- 디스크 I/O가 이벤트 루프를 블로킹
- 동일 파일을 요청마다 반복 파싱 (JSON 파싱은 CPU-bound)
- 100 TPS에서 100회/초 파일 오픈

**수정 방법**:
1. 서버 시작 시 한 번 로드하여 메모리에 캐시
2. 파일 변경 감지가 필요하면 `watchdog` 또는 mtime 체크

### H8. get_scan_from_db 반환 타입 불일치

**심각도**: HIGH
**파일**: `app/services/supabase_client.py`, line 103

**현재 상태**: `get_scan_from_db()`가 `dict | None`을 반환하지만, 호출부 (`main.py` line 202-204)에서 `ScanResponse` 모델을 기대.

```python
# main.py line 193-208
async def get_scan(scan_id: str):
    result = get_cached_scan(scan_id)  # ScanResponse | None
    if result is None:
        result = await get_scan_from_db(scan_id)  # dict | None !!
        if result:
            return result  # dict를 ScanResponse로 반환 시도 → 검증 실패 가능
```

**문제점**: Supabase fallback 경로에서 Pydantic 검증 없이 raw dict 반환. `response_model=ScanResponse`가 설정되어 있으므로 FastAPI가 자동 검증하지만, dict 구조가 다르면 500 에러.

**수정 방법**: `get_scan_from_db()`에서 `ScanResponse(**row)` 반환하거나, ScanResponse.model_validate() 사용

---

## MEDIUM Issues

### M1. 글로벌 mutable state가 모듈 import 시점에 초기화

**심각도**: MEDIUM
**파일**: `routes/profile_routes.py` line 122, `routes/index_routes.py` line 68-69

**현재 상태**: `_load_profiles()`가 모듈 임포트 시점에 호출 (line 122). 테스트에서 모듈 임포트만으로 Supabase 연결 시도.

**수정 방법**: `@app.on_event("startup")` 또는 `lifespan` context manager에서 초기화

### M2. 에러 응답에 내부 에러 타입명 노출

**심각도**: MEDIUM
**파일**: `app/main.py`, line 189, 314, 632, 816

**현재 상태**: `f"Scan failed: {type(e).__name__}: {str(e)[:200]}"` — 내부 예외 클래스명과 메시지를 클라이언트에 반환.

**수정 방법**: 프로덕션에서는 generic 메시지만 반환, 디버그 정보는 로그에만

### M3. ssl=False 하드코딩

**심각도**: MEDIUM
**파일**: `scanner.py` line 432, `main.py` 내 authenticated_scan

**현재 상태**: 모든 외부 요청에서 SSL 검증 비활성화. 스캐너가 대상의 TLS를 평가하면서 자체는 검증 안 하는 모순.

**수정 방법**: 기본적으로 SSL 검증 활성화, 실패 시 retry with ssl=False (그리고 이를 스캔 결과에 반영)

### M4. _validate_scan_url에서 URL redirection 미검증

**심각도**: MEDIUM
**파일**: `scanner.py`

**현재 상태**: URL 검증은 최초 URL에만 수행. aiohttp `allow_redirects=True`이므로 공격자가 공개 URL → 내부 URL로 리다이렉트 가능.

**수정 방법**: `allow_redirects=False`로 변경하고 수동으로 리다이렉트 체인 검증

### M5. 동시 스캔 제한 없음

**심각도**: MEDIUM
**파일**: `scanner.py`

**현재 상태**: 동시 스캔 수에 제한 없음. `TCPConnector(limit=20)`은 커넥션 풀 제한이지 동시 스캔 수 제한이 아님.

**수정 방법**: `asyncio.Semaphore(max_concurrent_scans)` 추가

### M6. playbook 엔드포인트에서 ScanResponse를 dict처럼 접근

**심각도**: MEDIUM
**파일**: `app/main.py`, lines 1745-1746

**현재 상태**:
```python
cached = get_cached_scan(scan_id)  # ScanResponse (Pydantic model)
dimensions = cached.get("dimensions", {})  # .get()은 dict 메서드
```

Pydantic 모델에 `.get()`을 호출하면 AttributeError 발생 가능 (Pydantic v2에서는 dict-like access 미지원).

**수정 방법**: `cached.dimensions` 직접 접근, 또는 `cached.model_dump()`

### M7. URL 비교 로직의 취약한 substring 매칭

**심각도**: MEDIUM
**파일**: `app/main.py`, line 282

**현재 상태**:
```python
if clean_url.rstrip("/") in s.get("url", "").rstrip("/") or s.get("url", "").rstrip("/") in clean_url.rstrip("/"):
```

**문제점**: `stripe.com`이 `stripe.com/pricing`과 매칭, `api.com`이 `api.company.com`과 매칭 등 false positive

**수정 방법**: URL 정규화 후 도메인 단위 비교

---

## LOW Issues

### L1. 함수 내부 반복 import

**심각도**: LOW
**파일**: `app/main.py`

**현재 상태**: `import json`, `import aiohttp`, `import re`가 8곳에서 함수 내부 반복 임포트

**수정 방법**: 파일 상단에서 한 번만 import

### L2. WaitlistRequest에 이메일 검증 없음

**심각도**: LOW
**파일**: `app/models.py`, line 67

**현재 상태**: `email: str` — Pydantic `EmailStr` 미사용

**수정 방법**: `email: EmailStr` 사용 (`pip install pydantic[email]`)

### L3. _generate_scan_id 충돌 가능성

**심각도**: LOW
**파일**: `scanner.py`, line 29

**현재 상태**: SHA256의 앞 12자만 사용. 충돌 확률은 낮지만 같은 URL을 같은 초에 스캔하면 동일 ID 생성.

**수정 방법**: `uuid.uuid4()` 사용 또는 hash 길이 증가

### L4. 테스트 부재

**심각도**: LOW

**현재 상태**: tests/ 디렉토리 또는 테스트 파일이 보이지 않음.

**수정 방법**: 최소한 scanner.py, recommender.py, tool_scorer.py에 대한 단위 테스트 추가

---

## Architecture Recommendations (우선순위순)

### 1단계: 긴급 (1주)
- [ ] C3: tool_scorer.py 데드코드 수정 (5분)
- [ ] C2: 캐시에 maxsize 추가 (cachetools 도입) (1시간)
- [ ] H4: asyncio.gather에 return_exceptions=True (10분)
- [ ] H5: rate store를 TTLCache로 교체 (30분)
- [ ] M6: playbook의 dict-like 접근 수정 (10분)

### 2단계: 중요 (2주)
- [ ] C1: main.py 분리 — routes/ 하위로 엔드포인트 이동
- [ ] C4: Supabase 호출을 asyncio.to_thread로 감싸기
- [ ] H1: 프로필 저장을 Supabase 단일 소스로 전환
- [ ] H7: prebuilt-scans.json 시작 시 1회 로드
- [ ] H8: get_scan_from_db 반환 타입 통일

### 3단계: 개선 (1개월)
- [ ] H2: SafeResolver로 SSRF 방어 강화
- [ ] H3: TF-IDF 최적화 또는 벡터 DB 이관
- [ ] H6: 인증 스캔 API 키 메모리 정리
- [ ] M1: 모듈 초기화를 lifespan으로 이동
- [ ] L4: 핵심 모듈 테스트 작성

### 4단계: 확장 (장기)
- [ ] Redis 캐시 도입 (멀티 인스턴스 지원)
- [ ] 벡터 DB로 추천 엔진 이관
- [ ] 구조화된 로깅 (structlog)
- [ ] OpenTelemetry 트레이싱

---

## Metrics Summary

| 항목 | 현재 값 | 목표 |
|------|---------|------|
| main.py 줄 수 | 2,908 | < 200 |
| 전체 코드베이스 | ~12,100줄 | - |
| 인메모리 캐시 수 | 4곳 (크기 제한 없음) | 1곳 (Redis) |
| 테스트 커버리지 | 0% | > 60% |
| 함수 내부 import | 8곳 | 0 |
| 데드코드 | 16줄 | 0 |
| ssl=False 하드코딩 | 2곳 | 0 |
