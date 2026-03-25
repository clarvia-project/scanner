# AI 에이전트 전용 마케팅 전략: Clarvia 딥리서치

> 작성일: 2026-03-25
> 목표: 인간 마케팅 제로, AI 에이전트가 자동으로 Clarvia를 발견/추천하는 전략

---

## 1. AI 에이전트 디스커버리 표준/프로토콜

### 핵심 발견
- llms.txt는 Jeremy Howard(Answer.AI)가 2024년 9월 제안한 커뮤니티 표준으로, 784+ 사이트가 구현했지만 아직 공식 W3C/IETF 표준은 아님
- .well-known/mcp.json (SEP-1649, SEP-1960)은 MCP 서버 자동 발견의 핵심이며, Anthropic/GitHub/Microsoft가 지원하지만 아직 코어 스펙에 미병합
- Schema.org 구조화 데이터가 있는 페이지는 AI 인용 확률 2-3배 높음 (65% of AI-cited pages include structured data)

### 상세 내용

#### llms.txt
- **제안자**: Jeremy Howard (Answer.AI), 2024년 9월
- **구현 현황**: 784+ 사이트 (전체 30만 도메인 중 10.13%)
- **주요 구현체**: Cloudflare, Anthropic, Vercel, Supabase, ElevenLabs
- **AI 실제 활용**: 공식 발표 없으나, Microsoft/OpenAI 크롤러가 실제로 llms.txt를 인덱싱하는 것이 확인됨. Windsurf는 llms.txt가 토큰 절약에 도움된다고 명시
- **현실**: SE Ranking 분석에 따르면 현재 AI 인용에 직접적 영향은 제한적이나, 미래 표준화 가능성 높음

#### .well-known/ai-plugin.json
- ChatGPT 플러그인 시스템과 함께 도입되었으나, ChatGPT 플러그인이 GPTs로 전환되면서 단독 표준으로서의 의미는 약화
- 현재는 MCP 기반 표준으로 대체되는 추세

#### .well-known/agents.json
- JSON Agents 표준 (jsonagents.org)이 프레임워크 무관한 에이전트 매니페스트로 부상
- Wildcard의 agents.json은 기존 API에 에이전트를 연결하는 경량 솔루션
- MCP와 보완적으로 사용 가능 (MCP는 연결, agents.json은 발견)

#### MCP Server Cards (SEP-1649 / SEP-1960)
- **SEP-1649**: `/.well-known/mcp/server-card.json` - 서버 메타데이터 (설명, 홈페이지, 도구 목록)
- **SEP-1960**: `/.well-known/mcp` - 엔드포인트 열거 및 인증 발견
- **상태**: Draft, 광범위한 커뮤니티 지지, 주요 MCP 클라이언트에서 구현 중
- **구현**: 두 가지 모두 구현 권장

#### Schema.org 구조화 데이터
- FAQ 스키마가 2026년 AI 인용에 가장 큰 영향
- JSON-LD 형식 선호 (HTML과 분리되어 프로그래밍적 파싱 용이)
- NLWeb(구조화 데이터 기반)이 대화형 AI 인터페이스의 핵심 기술로 부상

#### robots.txt LLM 지시자
- GPTBot(OpenAI 훈련), OAI-SearchBot(ChatGPT 검색), Claude-Web(Anthropic) 등 주요 AI 크롤러 User-Agent 존재
- 상위 1000 사이트 중 21%가 GPTBot 관련 규칙 보유
- ai.txt 제안 (2025): AI 상호작용 허용 범위를 선언하는 DSL, 아직 초기 단계

### Clarvia 액션 아이템

| 액션 | 난이도 | 임팩트 |
|------|--------|--------|
| llms.txt / llms-full.txt 최적화 (이미 있으므로 내용 보강) | 쉬움 | 보통 |
| .well-known/mcp/server-card.json 구현 (SEP-1649) | 보통 | 높음 |
| .well-known/mcp 매니페스트 구현 (SEP-1960) | 보통 | 높음 |
| Schema.org JSON-LD 추가 (SoftwareApplication, FAQPage) | 쉬움 | 높음 |
| robots.txt에 OAI-SearchBot, PerplexityBot 명시 허용 | 쉬움 | 보통 |
| agents.json 최적화 (이미 있으므로 JSON Agents 표준 준수 확인) | 쉬움 | 보통 |

---

## 2. AI 에이전트가 도구를 선택하는 메커니즘

### 핵심 발견
- Claude Code는 도구 설명(이름, 설명, 파라미터)을 기반으로 BM25/Regex 매칭하여 동적으로 도구를 로드 (Tool Search)
- 에이전트 프레임워크(LangChain/CrewAI)는 도구 설명의 품질이 선택의 핵심 결정요인
- Cursor/Windsurf 등 IDE 에이전트는 MCP 서버 설정을 통해 도구를 접근하며, 도구 설명 기반으로 LLM이 선택

### 상세 내용

#### Claude Code의 도구 발견
- **Tool Search**: MCP 도구 설명이 컨텍스트 윈도우 10% 초과 시 자동 활성화
- **매칭 방식**: Regex 모드 (정확 매칭) + BM25 모드 (시맨틱 유사도)
- **검색 대상**: 도구 이름, 설명, 파라미터 이름
- **효과**: 전통 방식 77K 토큰 -> Tool Search 8.7K 토큰 (85% 감소)
- **자동 새로고침**: list_changed 알림으로 동적 도구 업데이트 지원

#### ChatGPT/GPTs
- GPT Store에서 사용자가 GPT를 선택하면 내장 도구 사용
- Actions(이전 플러그인)를 통해 외부 API 호출
- OpenAPI 스키마 기반으로 도구 이해

#### Cursor / Windsurf
- mcp.json 설정 파일에서 MCP 서버 목록 로드
- 에이전트가 도구 설명 기반으로 자동 선택
- Windsurf는 엔터프라이즈 관리 기능 추가 제공
- 아직 초기 단계로 도구 선택 정확도에 차이 존재

#### LangChain / CrewAI
- **LangChain**: 개발자가 도구를 명시적으로 바인딩, LLM이 설명 기반으로 선택. 세밀한 제어 가능
- **CrewAI**: 역할/목표/배경 기반 에이전트에 도구 할당. 오케스트레이션 중심
- 두 프레임워크 모두 MCP 도구 통합 지원

#### 도구 선택 결정 기준 (공통)
1. **도구 이름의 명확성**: 기능을 즉시 파악 가능한 이름
2. **설명의 구체성**: 언제, 왜, 어떻게 쓰는지 명확
3. **파라미터 설명**: 각 파라미터의 용도와 타입 명시
4. **컨텍스트 매칭**: 현재 작업과 도구 설명의 시맨틱 유사도

### Clarvia 액션 아이템

| 액션 | 난이도 | 임팩트 |
|------|--------|--------|
| MCP 서버 11개 도구의 이름/설명을 AEO 키워드 최적화 | 쉬움 | 높음 |
| 각 도구 파라미터에 상세 설명 및 예시 추가 | 쉬움 | 높음 |
| OpenAPI 스키마 최적화 (ChatGPT Actions 호환) | 보통 | 보통 |
| 도구 설명에 "when to use" / "when not to use" 패턴 적용 | 쉬움 | 높음 |

---

## 3. MCP 레지스트리/마켓플레이스 생태계

### 핵심 발견
- 공식 MCP Registry (Anthropic/GitHub/Microsoft 지원)가 2025년 9월 프리뷰 런칭, server.json 기반 등록
- Smithery.ai에서 2,500+ 서버 중 8개만 5만+ 설치를 달성 — 상위 진입 시 독점적 노출 기회
- PulseMCP이 14,274+ 서버로 가장 큰 디렉터리, 인기도 기반 정렬 제공

### 상세 내용

#### 공식 MCP Registry (registry.modelcontextprotocol.io)
- **후원**: Anthropic, GitHub, PulseMCP, Microsoft
- **등록**: server.json 파일 제출 + 네임스페이스 인증 (역 DNS 형식: io.github.username/server)
- **현재 규모**: 87 서버 (엄격한 검증)
- **특징**: 자동 검증, 거버넌스, 하위 레지스트리 자동 전파
- **상태**: 프리뷰 (GA 전 변경 가능)

#### Smithery.ai
- **규모**: 2,500+ MCP 서버
- **특징**: 설치 관리 플랫폼, CLI 제공, 엔터프라이즈 관리
- **성장**: 2025년 3월 서버 생성 3배 급증
- **인사이트**: 5만+ 설치 서버가 8개뿐 -> 상위 진입 허들 높지 않음
- **등록**: smithery.ai 웹사이트에서 직접 제출

#### Glama.ai
- **특징**: 가장 포괄적인 MCP 레지스트리로 자칭
- **차별점**: 서버 품질 분석, 구조화된 메타데이터
- **등록**: 웹사이트 제출

#### PulseMCP
- **규모**: 14,274+ 서버 (가장 큰 디렉터리)
- **특징**: 인기도 정렬, 공식/커뮤니티 분류, 방문자 수 추정
- **MCP 서버도 제공**: pulsemcp-server로 디렉터리 자체를 AI가 검색 가능

#### mcp.so
- 초기 커뮤니티 디렉터리
- PulseMCP, Smithery에 비해 규모 작음

#### MCPHub.tools
- 서버 탐색 및 클라이언트 연동
- 상세 정보 및 설치 가이드 제공

#### npm 패키지 자동 인덱싱
- @modelcontextprotocol 스코프 패키지는 자동 발견 가능
- @mcpmarket/mcp-auto-install이 자동 발견 지원
- npm 게시 시 PulseMCP 등 자동 크롤링됨

#### MAU/도달범위 추정
- 공식 수치 미공개이나, MCP 생태계 전체가 급성장 중
- Smithery는 엔터프라이즈 포커스로 전환 중
- PulseMCP는 개발자 대상 디스커버리에 집중

### Clarvia 액션 아이템

| 액션 | 난이도 | 임팩트 |
|------|--------|--------|
| 공식 MCP Registry에 Clarvia MCP 서버 등록 | 보통 | 높음 |
| Smithery.ai에 등록 | 쉬움 | 높음 |
| PulseMCP에 등록 | 쉬움 | 높음 |
| Glama.ai에 등록 | 쉬움 | 보통 |
| mcp.so에 등록 | 쉬움 | 낮음 |
| MCPHub.tools에 등록 | 쉬움 | 낮음 |
| npm @clarvia 스코프로 MCP 서버 패키지 게시 | 보통 | 높음 |
| server.json 표준 준수로 자동 전파 활용 | 보통 | 높음 |

---

## 4. AI 검색 엔진 최적화 (AEO/GEO)

### 핵심 발견
- Perplexity는 3단계 리랭킹 + 신선도 편향이 강력하며, 12개월 이상 미업데이트 콘텐츠는 인용 탈락
- ChatGPT Search는 OAI-SearchBot 크롤러 기반이며, SSR + llms.txt + 시맨틱 헤더가 핵심
- Google AI Overviews는 E-E-A-T + 134-167 단어 자족적 답변 단위를 선호 (시맨틱 완전성 8.5+/10이면 인용 확률 4.2배)

### 상세 내용

#### Perplexity AI 최적화
- **소스 선택 메커니즘**: 3단계 리랭킹 시스템 + 수동 권위 도메인 리스트 + 신선도 + 토픽 멀티플라이어
- **핵심 요소**:
  - 구체적 수치와 데이터 포함 (추상적 주장은 무시)
  - 12개월 이내 업데이트 필수
  - 명시적 저자 + 크레덴셜
  - robots.txt에서 PerplexityBot 허용 필수
  - FAQPage, Article 스키마 + 저자 속성
- **타임라인**: 잘 최적화된 콘텐츠 시 2-4주 내 첫 인용 가능

#### ChatGPT Search
- **크롤러**: OAI-SearchBot (검색), ChatGPT-User (실시간), GPTBot (훈련용, 차단 가능)
- **핵심 요소**:
  - SSR (서버사이드 렌더링) 필수 — JavaScript 전용 렌더링 비선호
  - llms.txt 파일이 AI 사이트맵 역할
  - 시맨틱 헤더 + 마크다운 형식 선호
  - 인덱싱까지 3-14일
- **차단 주의**: GPTBot 차단 시에도 OAI-SearchBot은 별도 허용 필요

#### Google AI Overviews
- **선택 기준**:
  - E-E-A-T 신호 강한 소스 96% 인용
  - 15+ 인식된 엔티티 보유 페이지 4.8배 높은 선택 확률
  - 시맨틱 완전성 8.5+/10이면 4.2배 인용 확률
  - 134-167 단어 자족적 답변 단위 선호
- **중요**: 2026년 상위 10 랭킹 페이지에서의 인용이 76% -> 38%로 하락 — 순위 낮아도 AI 인용 가능

#### Claude 웹 검색
- 웹 검색 활성화 시 실시간 정보 수집
- 구체적이고 전문적인 콘텐츠 선호
- llms.txt 적극 활용 (Anthropic이 직접 권장)

#### "MCP server quality" / "AEO scanner" 쿼리 노출 전략
- 해당 정확 키워드를 타겟팅한 전문 콘텐츠 필요
- 구체적 데이터 (벤치마크, 비교표) 포함
- 자주 업데이트되는 리소스 페이지

### Clarvia 액션 아이템

| 액션 | 난이도 | 임팩트 |
|------|--------|--------|
| 12,800+ 도구별 프로필 페이지에 JSON-LD 스키마 추가 | 보통 | 높음 |
| SSR 보장 (모든 페이지가 JavaScript 없이 렌더링 가능) | 보통 | 높음 |
| 2주마다 핵심 콘텐츠 업데이트 (Perplexity 신선도 대응) | 보통 | 높음 |
| 각 페이지에 134-167 단어 자족적 답변 블록 배치 | 보통 | 높음 |
| OAI-SearchBot, PerplexityBot, ClaudeBot 명시 허용 | 쉬움 | 보통 |
| "AEO scanner" "MCP quality" 키워드 타겟 전문 콘텐츠 작성 | 보통 | 높음 |

---

## 5. 에이전트-투-에이전트 추천 네트워크

### 핵심 발견
- A2A (Agent-to-Agent) 프로토콜이 MCP와 보완적으로 발전 중 — MCP는 도구 연결, A2A는 에이전트 간 협업
- MCP 서버를 에이전트로 노출(as_mcp_server())하여 다른 에이전트가 호출하는 패턴이 부상
- Clarvia MCP 서버가 AEO 점수를 제공하면, 다른 에이전트가 도구 선택 시 Clarvia 점수를 참조하는 자연스러운 네트워크 효과 가능

### 상세 내용

#### A2A + MCP 결합 패턴
- A2A: 에이전트 간 네트워크 (발견, 위임, 협업)
- MCP: 에이전트-도구 연결 (도구 호출, 데이터 접근)
- 감독 에이전트가 A2A로 전문 에이전트를 발견 -> 전문 에이전트가 MCP로 도구 호출

#### 에이전트 카드 (Agent Card)
- 에이전트의 고수준 역량을 설명하는 메타데이터
- 다른 에이전트가 이 카드를 읽고 적합한 에이전트 선택
- Clarvia MCP 서버도 Agent Card 형태로 노출 가능

#### 네트워크 효과 시나리오
1. 개발자가 Clarvia MCP 서버 설치
2. 코딩 에이전트가 "이 MCP 서버의 품질은?" 질문받음
3. Clarvia MCP 도구 `analyze_server`를 호출
4. 결과에 Clarvia AEO 점수 + 개선 제안 포함
5. 개선 제안에 다른 도구/서버 정보 포함 -> 간접적 추천 네트워크

#### MCP 게이트웨이/디스커버리 미들웨어
- 도구 수 증가에 따라 MCP 게이트웨이가 에이전트의 도구 탐색을 지원
- Clarvia가 이 미들웨어 역할을 할 수 있음

### Clarvia 액션 아이템

| 액션 | 난이도 | 임팩트 |
|------|--------|--------|
| MCP 서버 응답에 "관련 도구 추천" 필드 추가 | 보통 | 높음 |
| A2A Agent Card 형식으로 Clarvia 에이전트 역량 공개 | 어려움 | 높음 |
| Clarvia를 MCP 디스커버리 미들웨어로 포지셔닝 | 어려움 | 높음 |
| analyze_server 결과에 "이 서버를 찾는 데 Clarvia 사용됨" 워터마크 | 쉬움 | 보통 |
| 다른 MCP 서버 개발자에게 Clarvia 배지/점수 임베드 제안 | 보통 | 높음 |

---

## 6. 프로그래매틱 SEO/콘텐츠

### 핵심 발견
- AI 에이전트는 완벽한 Schema 마크업이 있는 프로그래매틱 페이지를 "최소 저항 경로"로 선호
- 2,900+ 단어 기사는 평균 5.1 AI 인용, 800 미만은 3.2 — 긴 콘텐츠가 유리
- LLM은 순위 낮은 페이지라도 맥락적으로 관련 있으면 인용 — 소규모 도메인에 기회

### 상세 내용

#### 12,800+ 도구별 프로필 페이지
- 각 도구마다 자동 생성된 프로필 페이지 = 12,800개의 AI 인용 가능 진입점
- 필수 요소:
  - SoftwareApplication JSON-LD 스키마
  - AEO 점수 + 개선 제안 (독점 데이터)
  - 도구 기능, 프로토콜 지원, 호환성 정보
  - 134-167 단어 자족적 답변 블록
  - 구조화된 비교 데이터

#### 비교 페이지 자동 생성
- "Supabase MCP vs Firebase MCP" 같은 페어 비교
- 12,800개 도구 기준 수천만 개의 비교 조합 가능 (실질적으로 상위 인기 조합 선별)
- AI가 비교 질문에 답할 때 인용할 구조화된 데이터 제공
- 비교표 + 장단점 + 점수 차이

#### 카테고리 랜딩 페이지
- "Database MCP Servers", "Authentication Tools" 등 카테고리별
- 상위 도구 랭킹 + 트렌드 데이터
- AI가 "best MCP server for X" 질문에 인용

#### AI 검색 인용을 위한 핵심 기법
- 모든 페이지에 FAQ 섹션 (FAQPage 스키마)
- 구체적 수치 (점수, 순위, 비교 데이터)
- 매주/매월 자동 업데이트 (신선도 유지)
- SSR 필수

### Clarvia 액션 아이템

| 액션 | 난이도 | 임팩트 |
|------|--------|--------|
| 12,800개 도구 프로필 페이지에 SoftwareApplication JSON-LD 추가 | 보통 | 높음 |
| 상위 500 인기 도구 쌍의 비교 페이지 자동 생성 | 보통 | 높음 |
| 20개 카테고리 랜딩 페이지 생성 | 보통 | 높음 |
| 각 페이지에 FAQ 섹션 + FAQPage 스키마 | 보통 | 높음 |
| 주간 자동 업데이트 시스템 (점수 재계산 + 페이지 갱신) | 어려움 | 높음 |
| 각 페이지에 134-167 단어 답변 블록 템플릿 적용 | 쉬움 | 높음 |

---

## 7. 실제 사례 연구

### 핵심 발견
- "AI 에이전트만으로 성장한 서비스" 사례는 아직 문서화된 것이 거의 없음 — Clarvia가 선례가 될 기회
- Smithery의 MCP 생태계에서 상위 8개 서버만 5만+ 설치 — 초기 시장 선점 효과 큼
- llms.txt 도입 효과는 측정이 어려우나, Anthropic이 직접 Mintlify에 구현을 요청한 것은 강력한 시그널

### 상세 내용

#### MCP 레지스트리 등록 후 성장
- Smithery: 2025년 3월 서버 생성 3배 급증, 전체 2,500+ 서버
- 상위 8개만 5만+ 설치 = 상위 0.3%에 들면 극적인 노출
- MCP 생태계 성장이 "공급 사이드" 중심으로 폭발 -> 도구 자체보다 발견 도구가 핵심

#### llms.txt 도입 효과
- 직접적 트래픽 변화 데이터는 공개된 것이 거의 없음
- SE Ranking의 30만 도메인 분석: 현재 시점에서 AI 인용에 직접적 영향 미미
- 그러나 Windsurf, Claude 등이 llms.txt를 실제 사용하는 것이 확인됨
- "미래에 대한 투자" 성격이 강함

#### 프로그래매틱 SEO + AI 인용 사례
- 프로그래매틱 SEO 도구를 사용한 브랜드들이 30-80% 유기적 트래픽 증가
- AI Overviews가 비상위 순위 페이지도 인용하기 시작 (76% -> 38%로 상위 10 의존도 하락)
- 소규모 도메인에 콘텐츠 길이가 ChatGPT 인용에 65% 더 큰 영향

#### Clarvia의 선례 기회
- "AI 에이전트만으로 마케팅하는 서비스"라는 내러티브 자체가 PR 가치
- 이 실험의 결과를 데이터와 함께 공개하면 -> AEO 분야 권위 확립
- 자체 사례 연구가 콘텐츠 마케팅이 됨 (역설적이지만 "AI가 인용할 데이터" 생산)

### Clarvia 액션 아이템

| 액션 | 난이도 | 임팩트 |
|------|--------|--------|
| Clarvia 자체 AEO 점수 변화를 추적하는 대시보드 공개 | 보통 | 높음 |
| "에이전트 전용 마케팅 실험" 데이터를 정기 공개 | 보통 | 높음 |
| MCP 서버 설치 수 추적 시스템 구축 | 보통 | 보통 |

---

## 우선순위 매트릭스

### 임팩트 높음 + 난이도 쉬움 (즉시 실행)

| # | 액션 | 예상 소요 |
|---|------|----------|
| 1 | MCP 서버 11개 도구의 이름/설명을 AEO 키워드 최적화 + "when to use" 패턴 적용 | 1일 |
| 2 | Schema.org JSON-LD 추가 (SoftwareApplication + FAQPage) on clarvia.art | 1일 |
| 3 | 각 페이지에 134-167 단어 자족적 답변 블록 배치 | 1-2일 |
| 4 | robots.txt에 OAI-SearchBot, PerplexityBot, ClaudeBot 명시 허용 | 30분 |

### 임팩트 높음 + 난이도 보통 (이번 주 내)

| # | 액션 | 예상 소요 |
|---|------|----------|
| 5 | 모든 MCP 레지스트리에 등록 (공식 Registry, Smithery, PulseMCP, Glama) | 2-3일 |
| 6 | .well-known/mcp/server-card.json + .well-known/mcp 구현 | 1-2일 |
| 7 | npm 패키지로 MCP 서버 게시 (@clarvia 스코프) | 1일 |
| 8 | 12,800개 도구 프로필 페이지에 JSON-LD + FAQ 섹션 추가 | 3-5일 |
| 9 | SSR 보장 + llms.txt 내용 보강 | 1-2일 |
| 10 | "AEO scanner" "MCP quality" 키워드 타겟 콘텐츠 작성 | 2-3일 |

### 임팩트 높음 + 난이도 어려움 (2주 내)

| # | 액션 | 예상 소요 |
|---|------|----------|
| 11 | 상위 500 도구 비교 페이지 자동 생성 시스템 | 1주 |
| 12 | 20개 카테고리 랜딩 페이지 | 3-5일 |
| 13 | 주간 자동 업데이트 + 점수 재계산 시스템 | 1주 |
| 14 | A2A Agent Card + MCP 디스커버리 미들웨어 포지셔닝 | 2주 |
| 15 | MCP 서버 응답에 관련 도구 추천 + Clarvia 워터마크 | 3-5일 |

### 임팩트 보통 (백로그)

| 액션 | 난이도 |
|------|--------|
| agents.json JSON Agents 표준 준수 확인 | 쉬움 |
| mcp.so, MCPHub 등록 | 쉬움 |
| Clarvia 에이전트 마케팅 실험 데이터 정기 공개 | 보통 |
| 다른 MCP 서버 개발자에게 Clarvia 배지 임베드 제안 | 보통 |
| analyze_server 결과에 Clarvia 워터마크 | 쉬움 |

---

## TOP 5: 지금 당장 해야 할 것

### 1. MCP 레지스트리 올인 등록 (임팩트: 최상)
공식 MCP Registry + Smithery + PulseMCP + Glama에 동시 등록. server.json 표준 준수 시 하위 레지스트리 자동 전파. Smithery 상위 8개만 5만+ 설치라는 점에서 조기 진입이 핵심.

### 2. MCP 도구 설명 AEO 최적화 (임팩트: 최상)
AI 에이전트의 도구 선택은 설명 품질에 100% 의존. 11개 도구 각각에 "when to use / when not to use", 구체적 사용 사례, 파라미터 예시를 추가. Claude Code의 BM25/Regex 매칭에 최적화.

### 3. .well-known/mcp 엔드포인트 구현 (임팩트: 높음)
SEP-1649 server-card.json + SEP-1960 매니페스트 모두 구현. AI 클라이언트가 Clarvia 서버를 자동 발견할 수 있는 유일한 표준화 경로. 아직 Draft 단계라 선점 효과 극대.

### 4. 프로그래매틱 페이지 AI 최적화 (임팩트: 높음)
12,800개 도구 프로필에 JSON-LD 스키마 + 134-167단어 답변 블록 + FAQ 섹션. AI가 "best MCP server for X" 질문에 Clarvia 페이지를 인용하도록. SSR 필수.

### 5. npm 패키지 게시 + robots.txt 최적화 (임팩트: 높음)
npm @clarvia 스코프로 MCP 서버 게시하면 자동 디스커버리 대상. robots.txt에 OAI-SearchBot/PerplexityBot/ClaudeBot 명시 허용. 30분 작업으로 모든 AI 크롤러에 문을 열어두는 효과.

---

## 핵심 인사이트 요약

> **에이전트 전용 마케팅의 본질**: 인간이 읽을 필요 없는 메타데이터, 구조화 데이터, 표준 프로토콜을 통해 AI 시스템의 발견-평가-선택 파이프라인에 최적화하는 것.

> **시장 타이밍**: MCP 생태계가 "공급 폭발, 발견 부족" 상태. Clarvia는 발견 인프라(AEO 스캐너)를 제공하면서 동시에 자신이 발견되는 전략을 구사할 수 있는 독특한 포지션.

> **네트워크 효과**: Clarvia MCP 서버 설치 -> 도구 평가 시 Clarvia 점수 참조 -> 다른 개발자가 자기 도구의 Clarvia 점수를 올리려 함 -> Clarvia 인지도 증가. 이 루프가 핵심.

---

## 참고 소스
- [llms.txt 공식 사이트](https://llmstxt.org/)
- [llms.txt 채택 현황](https://www.llms-text.com/blog/sites-using-llms-txt)
- [SE Ranking llms.txt 분석](https://seranking.com/blog/llms-txt/)
- [MCP Registry 공식](https://registry.modelcontextprotocol.io/)
- [MCP Registry 소개 블로그](https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/)
- [SEP-1649 GitHub Issue](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1649)
- [SEP-1960 GitHub Issue](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1960)
- [.well-known/mcp 구현 가이드](https://www.wellknownmcp.org/tools/well-known)
- [Smithery.ai](https://smithery.ai/)
- [Glama.ai MCP Registry](https://glama.ai/mcp/servers)
- [PulseMCP](https://www.pulsemcp.com/)
- [MCP Registry Registry (Mastra)](https://mastra.ai/mcp-registry-registry)
- [Claude Code MCP 문서](https://code.claude.com/docs/en/mcp)
- [MCP Tool Search 설명](https://www.atcyrus.com/stories/mcp-tool-search-claude-code-context-pollution-guide)
- [Perplexity 소스 선택 알고리즘](https://authoritytech.io/blog/how-perplexity-selects-sources-algorithm-2026)
- [ChatGPT Search 인덱싱](https://www.clickrank.ai/how-to-get-indexed-in-chatgpt-search/)
- [Google AI Overviews 소스 선택](https://www.clickrank.ai/how-ai-overviews-select-the-source/)
- [AI Overviews 인용 하락 분석](https://almcorp.com/blog/google-ai-overview-citations-drop-top-ranking-pages-2026/)
- [AEO 완전 가이드 (Frase)](https://www.frase.io/blog/what-is-answer-engine-optimization-the-complete-guide-to-getting-cited-by-ai)
- [GEO 5가지 전략 (SEJ)](https://www.searchenginejournal.com/geo-strategies-ai-visibility-geoptie-spa/568644/)
- [Schema.org AI 검색 가이드](https://serpzilla.com/blog/schema-markup-ai-search/)
- [프로그래매틱 SEO + GEO](https://stormy.ai/blog/programmatic-seo-tools-generative-engine-optimization-2026)
- [robots.txt AI 크롤러 가이드](https://robotstxt.com/ai)
- [A2A vs MCP 비교](https://www.kdnuggets.com/building-ai-agents-a2a-vs-mcp-explained-simply)
- [JSON Agents 표준](https://jsonagents.org/)
- [7개 AI Agent-to-API 표준 비교](https://nordicapis.com/comparing-7-ai-agent-to-api-standards/)
- [LangChain vs CrewAI 도구 호출](https://www.scalekit.com/blog/unified-tool-calling-architecture-langchain-crewai-mcp)
- [MCP 생태계 분석 (Madrona)](https://www.madrona.com/what-mcps-rise-really-shows-a-tale-of-two-ecosystems/)
