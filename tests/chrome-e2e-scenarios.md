# Clarvia Chrome E2E Test Scenarios

> 실행 방법: Claude가 Chrome MCP (Claude in Chrome) 도구로 각 시나리오를 순서대로 실행
> 대상: clarvia.art (프로덕션)
> 판정: 각 VERIFY 항목 PASS/FAIL 기록 후 스크린샷 증거 수집

---

## E2E-01: 홈 → 스캔 → 결과

**목적**: 핵심 사용자 플로우 (URL 스캔) 정상 동작 확인
**이전 버그**: A2-1 (빈 화면)

```
STEPS:
1. navigate → https://clarvia.art
2. read_page → 홈 로드 확인
3. form_input → URL 입력란에 "https://httpbin.org" 입력
4. computer(click) → 스캔 버튼 클릭
5. (5초 대기)
6. read_page → 결과 페이지 확인

VERIFY:
- [ ] 홈페이지에 "AEO" 또는 "Agent Engine" 텍스트 존재
- [ ] URL 입력란 존재
- [ ] 스캔 버튼 클릭 가능
- [ ] 결과 페이지에 점수 표시 (숫자/100)
- [ ] 빈 화면 없음 (로딩 중이라도 스피너 or 텍스트 존재)
- [ ] /scan/ URL로 리다이렉트됨

SCREENSHOT: 결과 페이지
```

---

## E2E-02: 검색 + 필터 + 정렬

**목적**: 도구 검색, MCP 필터, 점수 정렬 정상 동작
**이전 버그**: A1-2 (정렬 깨짐), A1-3 (중복)

```
STEPS:
1. navigate → https://clarvia.art/tools
2. form_input → 검색란에 "database" 입력
3. read_page → 검색 결과 확인
4. computer(click) → "MCP" 필터 (있으면) 클릭
5. read_page → 필터 결과 확인

VERIFY:
- [ ] 검색 결과 > 0개
- [ ] 결과에 점수 표시됨
- [ ] 점수 내림차순 (위쪽 점수 >= 아래쪽 점수)
- [ ] 같은 도구 이름 중복 없음
- [ ] MCP 필터 적용 시 결과 변경됨

SCREENSHOT: 검색 결과 + MCP 필터 적용 후
```

---

## E2E-03: 상세 → 뱃지

**목적**: 도구 상세 페이지와 뱃지 점수 일치 확인
**이전 버그**: A1-5 (뱃지 점수 불일치)

```
STEPS:
1. navigate → https://clarvia.art/tools
2. computer(click) → 첫 번째 도구 클릭
3. read_page → 상세 페이지 점수 기록
4. read_page → 뱃지 섹션에서 뱃지 점수 확인

VERIFY:
- [ ] 상세 페이지에 점수 표시
- [ ] 4개 차원(Dimensions) 점수 표시
- [ ] Similar Tools 섹션 존재
- [ ] 뱃지 미리보기 존재 (있는 경우)

SCREENSHOT: 상세 페이지 전체
```

---

## E2E-04: 비교 페이지

**목적**: 도구 비교 기능 정상 동작, 등급 일치
**이전 버그**: A1-6 (등급 불일치), A1-7 (+ 버튼 이탈)

```
STEPS:
1. navigate → https://clarvia.art/compare
2. read_page → 비교 페이지 초기 상태 확인
3. form_input → 첫 번째 도구 검색란에 "supabase" 입력
4. computer(click) → 검색 결과에서 도구 선택
5. form_input → 두 번째 도구 검색란에 "firebase" 입력
6. computer(click) → 검색 결과에서 도구 선택
7. read_page → 비교 결과 확인

VERIFY:
- [ ] 비교 페이지 로드됨
- [ ] 도구 검색/추가 가능
- [ ] 2개 도구 사이드바이사이드 비교 표시
- [ ] 등급 표시 일관적 (Excellent/Strong/Moderate/Low)
- [ ] 비교 중 페이지 이탈 없음 (다른 페이지로 이동하지 않음)

SCREENSHOT: 비교 결과
```

---

## E2E-05: 카테고리 탐색

**목적**: 카테고리 목록 + 상세 정상 동작, 숫자 정합성
**이전 버그**: A3-1 (숫자 불일치), A3-2 (count:0)

```
STEPS:
1. navigate → https://clarvia.art/categories
2. read_page → 카테고리 목록 + 총 도구 수 확인
3. computer(click) → 첫 번째 카테고리 클릭
4. read_page → 카테고리 상세의 도구 목록 확인

VERIFY:
- [ ] 카테고리 카드들 표시됨
- [ ] 각 카테고리에 도구 수 > 0
- [ ] "s" 같은 유령 카테고리 없음
- [ ] 카테고리 클릭 시 도구 목록 표시
- [ ] 총 도구 수 숫자가 합리적 (27,000+)

SCREENSHOT: 카테고리 목록
```

---

## E2E-06: Playbook 탭 클릭 (미수정 High 버그)

**목적**: Playbook 탭 클릭 시 페이지 이탈 여부 확인
**이전 버그**: A2-2 (Node.js 탭 → 홈), A2-3 (항목 클릭 → /docs)

```
STEPS:
1. navigate → https://clarvia.art
2. form_input → URL 입력란에 "https://api.github.com" 입력
3. computer(click) → 스캔 버튼 클릭
4. (8초 대기 - 스캔 완료)
5. read_page → 스캔 결과 페이지 확인
6. computer(scroll) → Playbook 섹션까지 스크롤
7. computer(click) → Node.js/Python 탭 클릭
8. read_page → 현재 URL 확인

VERIFY:
- [ ] 스캔 결과 페이지에서 Playbook 섹션 존재
- [ ] 탭 클릭 후에도 같은 /scan/ URL 유지
- [ ] 홈(/)으로 이동하지 않음
- [ ] /docs로 이동하지 않음
- [ ] Playbook 항목 텍스트 클릭해도 이탈 없음

SCREENSHOT: Playbook 탭 클릭 후 URL 확인
```

---

## E2E-07: 검색 → 상세 → 뒤로가기 (미수정 High 버그)

**목적**: 뒤로가기 시 검색 상태 유지 확인
**이전 버그**: A1-4 (검색 상태 초기화)

```
STEPS:
1. navigate → https://clarvia.art/tools
2. form_input → 검색란에 "database" 입력
3. read_page → 검색 결과 확인 (결과 수 기록)
4. computer(click) → 첫 번째 결과 클릭
5. read_page → 상세 페이지 확인
6. go_back → 뒤로가기
7. read_page → 검색 상태 확인

VERIFY:
- [ ] 검색 결과가 정상 표시됨
- [ ] 상세 페이지로 이동 후 뒤로가기 가능
- [ ] 뒤로가기 후 "database" 검색어 유지
- [ ] 뒤로가기 후 검색 결과 동일
- [ ] 필터 상태도 유지 (필터 적용했을 경우)

SCREENSHOT: 뒤로가기 후 검색 상태
```

---

## E2E-08: 스캔 결과 → 뒤로가기 (미수정 Medium 버그)

**목적**: 스캔 결과에서 뒤로가기 시 홈으로 이동 확인
**이전 버그**: A2-6 (/leaderboard로 이동)

```
STEPS:
1. navigate → https://clarvia.art
2. form_input → URL 입력란에 "https://httpbin.org" 입력
3. computer(click) → 스캔 버튼 클릭
4. (5초 대기)
5. read_page → /scan/ URL 확인
6. go_back → 뒤로가기
7. read_page → 현재 URL 확인

VERIFY:
- [ ] 스캔 후 /scan/ URL에 있음
- [ ] 뒤로가기 후 홈(/) 또는 이전 페이지로 이동
- [ ] /leaderboard로 이동하지 않음
- [ ] 페이지 정상 표시

SCREENSHOT: 뒤로가기 후 URL
```

---

## E2E-09: 모바일 네비게이션

**목적**: 모바일 뷰포트에서 네비게이션 접근 가능 확인
**이전 버그**: B1 (모바일 네비 없음)

```
STEPS:
1. resize_window → 375x812 (iPhone 크기)
2. navigate → https://clarvia.art
3. read_page → 네비게이션 요소 확인
4. computer(click) → 햄버거 메뉴 (있으면) 클릭
5. read_page → 메뉴 항목 확인

VERIFY:
- [ ] 375px에서 페이지 깨지지 않음
- [ ] 네비게이션 접근 가능 (햄버거 메뉴 or 다른 방식)
- [ ] 주요 메뉴 항목 접근 가능 (Tools, Scan, Categories 등)
- [ ] URL 입력란 사용 가능

SCREENSHOT: 모바일 뷰
```

---

## E2E-10: 에이전트 디스커버리 파일

**목적**: AI 에이전트용 디스커버리 파일 정상 확인
**이전 버그**: A3-11 (숫자 불일치)

```
STEPS:
1. navigate → https://clarvia.art/.well-known/agents.json
2. read_page → JSON 파싱 확인
3. navigate → https://clarvia.art/llms.txt
4. read_page → 내용 확인
5. navigate → https://clarvia.art/robots.txt
6. read_page → AI 크롤러 규칙 확인

VERIFY:
- [ ] agents.json: 유효한 JSON
- [ ] agents.json: tools 배열 존재
- [ ] agents.json: 숫자가 실제와 근접 (27,000+)
- [ ] llms.txt: 에이전트 안내문 존재
- [ ] llms.txt: 숫자가 실제와 근접
- [ ] robots.txt: AI 크롤러 허용 규칙 존재

SCREENSHOT: agents.json 내용
```

---

## 실행 요약 템플릿

```
━━━ CHROME E2E TEST REPORT ━━━
실행일: YYYY-MM-DD
대상: clarvia.art

| ID | 시나리오 | 결과 | 주요 발견 |
|----|---------|------|-----------|
| E2E-01 | 홈→스캔→결과 | PASS/FAIL | |
| E2E-02 | 검색+필터 | PASS/FAIL | |
| E2E-03 | 상세→뱃지 | PASS/FAIL | |
| E2E-04 | 비교 | PASS/FAIL | |
| E2E-05 | 카테고리 | PASS/FAIL | |
| E2E-06 | Playbook 탭 | PASS/FAIL | |
| E2E-07 | 검색 뒤로가기 | PASS/FAIL | |
| E2E-08 | 스캔 뒤로가기 | PASS/FAIL | |
| E2E-09 | 모바일 네비 | PASS/FAIL | |
| E2E-10 | 디스커버리 파일 | PASS/FAIL | |

PASS: /10
FAIL: /10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
