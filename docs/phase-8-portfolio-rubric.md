# Phase 8 Portfolio Rubric

## Goal
phase 8의 LLM structured extraction 작업에서 무엇을 포트폴리오 핵심 성과로 삼을지 미리 고정하고, 구현 중 어떤 수치를 반드시 수집해야 하는지 정리한다.

## Delivery Rules
- phase는 `8.0 -> 8.6` 순서로 진행한다.
- 각 phase `n.x`마다 기능 구현 커밋 후 테스트/문서 커밋을 분리한다.
- 커밋 메시지는 한글 서술형으로만 작성하고 `feat`, `test`, `phase 8.x` prefix를 붙이지 않는다.
- 각 phase `n.x` 문서에는 `Problem -> Solution -> Result` 구조와 `Refactor Priorities(high / mid / low)`를 반드시 남긴다.
- `Refactor Priorities`에는 추후 개선 시 성능에 영향을 줄 수 있는지 `직접 있음 / 간접 있음 / 없음`으로 함께 표시한다.

## Scoring Rules
포트폴리오 가치는 10점 만점으로 아래 항목을 합산해 평가한다.

- AI relevance: 3점
- measurability: 3점
- technical defensibility: 2점
- story clarity: 2점

## Top 3 Candidates
### 1. 정규식 추출기를 LLM structured extraction으로 교체
- score: `9.4 / 10`
- Problem:
  - 현재 extractor는 정규식 기반이라 공지 형식이 바뀌거나 예외 문구가 섞이면 추출 실패 가능성이 높다.
- Solution:
  - canonical block과 block id를 포함한 context를 LLM에 주고, JSON schema 기반 structured output으로 `qualification + evidence`를 추출한다.
  - heuristic extractor는 fallback으로 유지한다.
- Result:
  - field-level exact match
  - extraction success rate
  - evidence valid rate
  - regex baseline 대비 accuracy improvement
- Observed synthetic result:
  - heuristic field exact match `54.17%`
  - llm field exact match `50.00%`, success rate `50.00%`
  - hybrid field exact match `79.17%`
  - hybrid가 heuristic 대비 field exact match를 `25.00%p` 개선
- Why this matters:
  - “AI를 핵심 로직에 사용했다”는 점이 가장 직접적으로 보인다.
  - deterministic eligibility와도 자연스럽게 이어진다.

### 2. provenance 기반 근거 유효성 보장
- score: `8.8 / 10`
- Problem:
  - LLM이 값을 맞게 뽑아도, 근거 블록과 연결되지 않으면 실서비스 설득력이 떨어진다.
- Solution:
  - LLM이 `block_id`를 반드시 반환하게 하고, backend가 이를 canonical block과 매핑해 provenance anchor로 저장한다.
- Result:
  - evidence valid rate
  - missing evidence rate
  - invalid block reference rate
  - explanation trace coverage
- Observed synthetic result:
  - successful extraction 기준 evidence valid rate `100.00%`
  - evidence coverage는 heuristic `57.14%`, llm `52.38%`, hybrid `80.95%`
  - hybrid가 heuristic 대비 evidence coverage를 `23.81%p` 개선
- Why this matters:
  - “왜 그렇게 판단했는가”를 말할 수 있어 금융/행정형 서비스에 강하다.

### 3. hybrid fallback으로 추출 안정성 확보
- score: `8.1 / 10`
- Problem:
  - 외부 LLM 호출은 timeout, invalid JSON, hallucinated evidence 등으로 실패할 수 있다.
- Solution:
  - `llm -> schema validation -> heuristic fallback` 경로를 만들고 retry/logging을 붙인다.
- Result:
  - pipeline success rate
  - fallback recovery rate
  - invalid output rate
  - extraction p95 latency
- Observed synthetic result:
  - llm success rate `50.00%`
  - hybrid success rate `100.00%`
  - hybrid fallback recovery rate `100.00%`
  - hybrid p95 latency `4.54ms`
- Why this matters:
  - 단순 PoC가 아니라 운영형 AI 서비스 설계라는 점을 보여준다.

## Metrics To Collect By Phase 8.6
- field-level exact match
- extraction success rate
- evidence valid rate
- invalid JSON rate
- fallback recovery rate
- extraction avg / p95 latency
- token usage and estimated cost

## Minimum Acceptable Result
- regex baseline 대비 핵심 field exact match 개선이 있어야 한다.
- evidence valid rate는 단순 accuracy보다 우선한다.
- fallback path가 없는 단일 happy-path demo는 포트폴리오 주력 성과로 쓰지 않는다.
- 현재 synthetic gold set 기준으로는 hybrid만 이 조건을 만족한다.

## Do Not Claim
- 실제 운영 환경에서의 production accuracy
- 의미 검색 품질 향상
- agent orchestration 고도화
- 금융 특화 AI 서비스 완성

## Best Portfolio Sentence Pattern
- 문제: 정규식 기반 추출기는 공지 형식 변화와 예외 문구에 취약했다.
- 해결: LLM structured extraction과 provenance block citation, heuristic fallback을 도입했다.
- 결과: 추출 정확도와 근거 유효성을 수치로 검증하고, deterministic eligibility와 연결되는 AI extraction pipeline을 만들었다.

## Best Current Story
- 문제: 정규식 기반 추출은 wording variation sample에서 학년, 학적, 제출서류 해석이 약했고, llm 단독 경로는 invalid evidence와 transport error에서 그대로 실패했다.
- 해결: canonical block 기반 structured extraction, provenance block validation, hybrid fallback을 같은 extractor contract 위에 올렸다.
- 결과: synthetic gold set `4건` 기준 hybrid mode는 success rate `100.00%`, field exact match `79.17%`, evidence coverage `80.95%`, fallback recovery `100.00%`를 기록했다.
