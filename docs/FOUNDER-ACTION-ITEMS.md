# Founder Action Items — 상호 직접 처리 필요

**Date**: 2026-03-27
**Prepared by**: Clarvia CEO Agent

---

## Overview

모든 자동화 및 엔지니어링 작업 중 **외부 권한, 비용 결정, 또는 전략적 판단**이 필요한 항목만 아래에 정리했습니다.
나머지는 CEO 에이전트가 자율적으로 처리합니다.

**우선순위 기준**:
- P0: 지금 당장 처리 안 하면 서비스 손상
- P1: 이번 주 안에 처리 필요
- P2: 이번 달 안에 처리 필요
- Strategic: 사장님만 판단 가능한 방향 결정

---

## P0 — 지금 당장 (서비스 영향)

### P0-1: Render 환경변수 설정 (Supabase 연결)

**현상**: 백엔드 헬스체크가 `"database": "not_configured"`를 반환합니다.
즉, **모든 스캔 결과, 에이전트 트래픽 데이터, 분석 데이터가 Render 재시작 시 소실**됩니다.
이것이 "analytics 45명 → 재시작 후 0명" 문제의 근본 원인입니다.

**해야 할 일**:
1. Render Dashboard → clarvia-api → Environment
2. 다음 환경변수 추가:
   ```
   SUPABASE_URL=<Supabase 프로젝트 URL>
   SUPABASE_ANON_KEY=<Supabase anon key>
   ```
3. 서비스 재배포 (Deploy latest commit)

**확인 방법**:
```bash
curl https://clarvia-api.onrender.com/health
# "database": "ok" 가 나와야 함
```

**시간**: 5분
**위험도**: 없음 (환경변수 추가만)

---

### P0-2: api.clarvia.art SSL 인증서 수정

**현상**: `api.clarvia.art`로 요청 시 SSL handshake 실패.
외부 개발자/에이전트가 api.clarvia.art를 사용하면 연결 불가.

**해야 할 일**:
1. Render Dashboard → clarvia-api → Custom Domains
2. `api.clarvia.art` 도메인 상태 확인
3. SSL 인증서 재발급 또는 도메인 재연결

**대안**: DNS에서 `api.clarvia.art → clarvia-api.onrender.com` CNAME 설정 확인
(Cloudflare 또는 도메인 레지스트라에서)

**시간**: 15-30분
**위험도**: 없음

---

## P1 — 이번 주 안에

### P1-1: npm 패키지 퍼블리시 (clarvia-mcp v1.1.1)

**현상**: MCP 서버 코드가 업데이트되었지만 npm에 v1.1.1이 퍼블리시되지 않았습니다.
현재 npm 최신 버전은 확인 필요. OTP(2FA) 때문에 자동화 불가.

**해야 할 일**:
```bash
cd /Users/sangho/클로드\ 코드/scanner/mcp-server
npm version patch  # or minor/major as appropriate
npm publish --otp=<your-otp-code>
```

**확인 방법**:
```bash
npm show clarvia-mcp version
```

**시간**: 5분
**위험도**: 낮음 (npm 퍼블리시)

---

### P1-2: Google Search Console 사이트맵 등록

**현상**: 사이트맵이 생성되어 있지만 Google Search Console에 등록되지 않았습니다.
등록하지 않으면 Google이 15,000개 툴 프로필 페이지를 크롤링하지 않습니다.

**해야 할 일**:
1. https://search.google.com/search-console → clarvia.art
2. Sitemaps → Add a new sitemap
3. `https://clarvia.art/sitemap.xml` 입력 → Submit

**시간**: 5분
**위험도**: 없음

---

### P1-3: UptimeRobot 모니터링 설정

**현상**: 백엔드 502 이슈가 있었으나 외부 모니터링이 없어 언제 발생했는지 추적 불가.

**해야 할 일**:
1. https://uptimerobot.com (무료 계정)
2. Add New Monitor → HTTP(S)
3. URL: `https://clarvia-api.onrender.com/health`
4. Check interval: 5 minutes
5. Alert: 이메일 또는 텔레그램 webhook

**시간**: 10분
**위험도**: 없음 (무료)

---

## P2 — 이번 달 안에

### P2-1: Supabase 테이블 스키마 확인

**현상**: 백엔드가 Supabase에 데이터를 쓰려고 시도하지만 `profiles` 테이블이 없으면 에러.

**해야 할 일**: Supabase Dashboard → SQL Editor에서 실행:
```sql
-- Check existing tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';

-- Required tables (if missing, run backend's schema migration)
-- profiles, scans, api_events, analytics
```

백엔드 팀(CEO 에이전트)이 필요한 SQL 스크립트를 제공할 수 있습니다.
사장님은 Supabase 어드민 접근 권한으로 실행만 하면 됩니다.

**시간**: 15분
**위험도**: 낮음 (읽기 먼저)

---

### P2-2: GitHub Repository 공개/비공개 결정

**현상**: `github.com/clarvia-project/scanner`가 public인지 private인지에 따라
awesome-mcp-servers PR 전략이 달라집니다.

**판단 요소**:
- Public → 커뮤니티 기여 가능, 코드 노출
- Private → 스코어링 알고리즘 보호, 협업 제한

**CEO 에이전트 추천**: Public으로 전환. 스코어링 알고리즘을 공개하는 것이 Glama 대비 신뢰성 차별화 포인트입니다.
단, `config.yaml`의 API 키와 환경변수는 절대 커밋하지 않습니다.

**시간**: 10분 결정

---

## Strategic — 방향 결정 필요

### Strategy-1: 모트 구축을 위한 데이터 공개 수준 결정

**질문**: Clarvia의 스코어링 데이터를 얼마나 공개할 것인가?

**옵션 A**: 완전 공개 (점수 공식, API 무제한)
- 장점: 신뢰성 최고, 에이전트 프레임워크 통합 용이
- 단점: 경쟁자가 방법론 복사 가능

**옵션 B**: 공식 공개 + 데이터 유료화
- 장점: 수익화 가능, 데이터 독점
- 단점: 초기 신뢰 구축 어려움

**옵션 C**: 방법론 공개 + 역사적 데이터 유료화
- 장점: 신뢰 + 수익 균형
- 단점: 복잡한 tiering

**CEO 에이전트 추천**: 옵션 C. 현재(무료) → 6개월 후 역사적 트렌드 데이터를 Pro 기능으로.

---

### Strategy-2: 도구 작성자 아웃리치 시작 시점

**현황**: Top 200 MCP 서버 작성자 리스트 생성 가능하지만,
아웃리치 이메일 발송은 자동화하면 스팸으로 처리될 위험이 있습니다.

**판단 필요**: 사장님이 직접 개인화된 이메일을 발송하거나,
공개 GitHub 이슈/PR로 접근하거나, 커뮤니티 포럼에 참여할지 결정.

**CEO 에이전트 기여**: 아웃리치 리스트 생성 + 메시지 템플릿 작성은 자동화.
실제 발송은 사장님이 직접.

---

### Strategy-3: 첫 번째 유료 고객 타겟 결정

**목표**: Month 6 — Tool Author Pro $49/month 론칭.

**질문**: 어떤 카테고리의 도구 작성자를 먼저 타겟할 것인가?
- MCP server 작성자 (현재 가장 많음, 가장 동기부여됨)
- API 플랫폼 (큰 회사들, 예산 있음, 의사결정 느림)
- CLI 툴 작성자 (개발자 친화적, 커뮤니티 영향력)

**CEO 에이전트 추천**: MCP server 작성자 먼저. 이들이 가장 점수에 민감하고,
README에 Clarvia badge를 달 동기가 가장 높습니다.

---

### Strategy-4: 에이전트 프레임워크 통합 파트너십 접근

**현황**: LangChain Hub, AutoGen, LangGraph 중 하나가 Clarvia API를 임베드하면
모트가 Lock-in 수준으로 강화됩니다.

**판단 필요**: 사장님이 LinkedIn/Discord/GitHub에서 해당 팀과 직접 연락 필요.
기술적 통합은 CEO 에이전트가 PR 제출 가능.

**CEO 에이전트 기여**: 통합 제안서 작성, 기술 문서, PR 초안.
실제 관계 구축은 사장님이 직접.

---

## 자동화 현황 요약

| 영역 | 자동화 완료 | 사장님 필요 |
|------|------------|------------|
| 도구 수집 | O (harvester 6am daily) | X |
| 스코어 캘리브레이션 | O (score_calibration Sun weekly) | X |
| 마케팅 상태 추적 | O (marketing_automation 9am daily) | X |
| 사이트맵 갱신 | O (sitemap_refresh Mon weekly) | X |
| 헬스체크 | O (every 5min) | X |
| 일일 리포트 | O (10pm daily via Telegram) | X |
| Supabase 연결 | X | O (P0-1: 환경변수 설정) |
| SSL 수정 | X | O (P0-2: Render 설정) |
| npm 퍼블리시 | X (OTP 필요) | O (P1-1: 5분) |
| Google Search Console | X | O (P1-2: 5분) |
| 도구 작성자 아웃리치 | X (리스트만 생성 가능) | O (Strategic-2) |
| 파트너십 접근 | X (문서만 작성 가능) | O (Strategic-4) |

---

*이 문서는 CEO 에이전트가 매주 업데이트합니다.*
*완료된 항목은 체크(✓)로 표시하고 날짜를 기록하세요.*
*Last updated: 2026-03-27*
