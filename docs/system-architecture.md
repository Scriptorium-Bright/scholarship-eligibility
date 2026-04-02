# System Architecture

## One-Line Summary
JBNU Scholarship Regulation Search & Eligibility Decision System은 장학 공지를 수집하고, 원문을 보존형으로 정규화한 뒤, 구조화 규정과 deterministic engine으로 검색과 지원 가능 여부를 제공하는 Python monolith다.

## Architecture Goals
- 비정형 공지를 단순 텍스트 검색이 아니라 `원문 저장 + 구조화 규정 + 판정 엔진`으로 분리한다.
- provenance가 없는 값은 신뢰하지 않는다.
- 최종 eligibility는 LLM이 아니라 코드 기반 엔진이 판정한다.
- 수집, 정규화, 추출, 검색, 판정 경로를 단계별로 재처리 가능하게 유지한다.

## High-Level Flow
```text
[JBNU Boards]
    |
    v
[Collectors / Parsers]
    |
    v
[Raw Storage]
  - notice HTML
  - attachment bytes
    |
    v
[Normalizers]
  -> canonical documents
    |
    v
[Rule Extractor]
  -> scholarship rules
  -> provenance anchors
    |
    v
[Search Read Model]
  -> search API
  -> open scholarship API
    |
    v
[Eligibility Engine]
  -> eligibility API
```

## Runtime Shape
- Application style: Python monolith + FastAPI
- API layer: FastAPI routers expose health, search, open scholarship, eligibility endpoints
- Service layer: orchestration logic for collection, normalization, extraction, search, and eligibility
- Repository layer: SQLAlchemy-based persistence and read queries
- Storage:
  - PostgreSQL/SQLite for notices, canonical documents, rules, provenance
  - local filesystem for raw HTML and attachment archival

## Core Data Model
### 1. Notice Layer
- `ScholarshipNotice`: 수집한 공고 메타데이터
- `NoticeAttachment`: 공고 첨부파일 메타데이터

### 2. Canonical Document Layer
- `CanonicalDocument`: notice/attachment를 정규화한 텍스트 문서
- `CanonicalBlock`: 검색과 provenance의 최소 텍스트 단위

### 3. Structured Rule Layer
- `ScholarshipRule`: 장학명, 신청 기간, qualification JSON, provenance key를 가진 구조화 규정
- `ProvenanceAnchor`: rule field가 어떤 canonical block에서 왔는지 가리키는 근거 포인터

### 4. Read / Decision Layer
- `ScholarshipSearchItem`: notice, rule, provenance를 묶은 검색 응답 모델
- `ScholarshipEligibilityItem`: search item에 decision, explanation, condition checks를 추가한 판정 응답 모델

## Layer Responsibilities
### Collectors
- 게시판 목록/상세 HTML을 파싱한다.
- 장학 관련 공지만 필터링한다.
- notice/attachment 메타데이터를 DB에 저장한다.
- 필요 시 raw HTML과 attachment 파일도 함께 보존한다.

### Raw Storage
- notice HTML 원문을 파일로 저장한다.
- attachment 원본 바이트를 파일로 저장한다.
- 이후 normalization 단계에서 같은 원문을 재사용할 수 있게 한다.

### Normalizers
- raw notice HTML을 canonical block 구조로 변환한다.
- PDF/HWP/text attachment를 canonical document로 변환한다.
- 검색과 추출이 같은 입력 구조를 쓰도록 만든다.

### Rule Extractor
- canonical document에서 장학명, GPA, 소득분위, 학년, 학적, 제출서류를 추출한다.
- heuristic baseline과 LLM structured extraction이 같은 extractor contract를 공유한다.
- `hybrid` 모드에서는 provider failure나 invalid evidence mapping 시 heuristic extractor로 fallback한다.
- 추출한 값마다 provenance anchor 후보를 만들고 extraction outcome log를 남긴다.
- 결과를 scholarship rule / provenance 테이블에 저장한다.

### Search Read Model
- published rule을 notice, document, provenance와 함께 읽는다.
- lexical scoring으로 검색 결과를 정렬한다.
- 현재 신청 가능한 공고 목록을 계산한다.
- 이후 eligibility engine이 재사용할 공용 read path 역할도 한다.
- 현재 구현에서는 후보 탐색 단계의 provenance eager assembly를 제거하고, 최종 응답 item에만 provenance를 hydrate한다.

### Eligibility Engine
- student profile과 structured qualification JSON을 직접 비교한다.
- `eligible`, `ineligible`, `expired`, `insufficient_info` 네 상태를 deterministic하게 계산한다.
- 각 조건의 passed/failed/missing 상태와 explanation을 함께 반환한다.

## Request Flows
### Search API
```text
GET /api/v1/scholarships/search
-> ScholarshipSearchService
-> published rules + notice + document load
-> lexical scoring
-> sort / limit
-> final item provenance hydrate
-> provenance-backed search response
```

### Open Scholarship API
```text
GET /api/v1/scholarships/open
-> ScholarshipSearchService
-> published rule read model load
-> application window filter
-> current open scholarship list
```

### Eligibility API
```text
POST /api/v1/scholarships/eligibility
-> ScholarshipEligibilityService
-> search path or published rule path load
-> EligibilityDecisionEngine
-> EligibilityAnswerBuilder
-> decision + explanation + condition diagnostics
```

## Why This Is Not a Simple RAG Chatbot
- 문서 chunk만 임베딩해서 답하지 않는다.
- raw document, canonical document, structured rule, provenance를 분리 저장한다.
- 최종 eligibility는 deterministic code가 판정한다.
- explanation도 provenance와 condition checks를 기준으로 조립한다.

## Current Strengths
- 수집부터 판정 API까지 end-to-end 흐름이 구현되어 있다.
- HTML/PDF/HWP를 같은 canonical document 계층으로 수렴시켰다.
- 검색과 판정을 분리하면서도 같은 structured rule 계층을 재사용한다.
- provenance anchor를 통해 근거 추적이 가능하다.
- heuristic, llm, hybrid 세 extraction mode를 같은 파이프라인 위에서 비교할 수 있다.

## Current Limits
- search는 아직 semantic embedding 없이 lexical scoring 중심이다.
- extraction 평가는 현재 synthetic gold set과 fake provider 기준이다.
- eligibility qualification schema가 현재는 핵심 필드 중심이다.

## Performance Note
- synthetic benchmark `1,500 rules / 12,000 provenance anchors` 기준으로 search API의 p95 latency를 `12.66s -> 5.07s`로 줄였다.
- 핵심 변경은 “모든 후보에 대해 provenance를 먼저 조립하지 않고, 최종 응답 item에만 hydrate한다”는 점이다.
- phase 8 synthetic gold set `4건` 기준으로 hybrid extraction은 heuristic 대비 field exact match를 `54.17% -> 79.17%`, evidence coverage를 `57.14% -> 80.95%`로 끌어올렸다.
- 같은 평가에서 llm 단독 success rate는 `50.00%`, hybrid fallback recovery rate는 `100.00%`였다.
- 자세한 측정 방법과 결과는 [docs/performance-benchmark.md](docs/performance-benchmark.md)에 정리했다.

## Interview Framing
- 이 시스템의 핵심은 “공지 수집기”가 아니라 “비정형 문서를 구조화된 의사결정 시스템으로 바꾸는 아키텍처”다.
- 문서 검색과 지원 가능 여부 판정을 분리한 이유는 정확성과 추적 가능성을 확보하기 위해서다.
- LLM을 전면에 세우지 않고, 구조화 규정과 deterministic engine을 중심에 둔 설계가 차별점이다.
