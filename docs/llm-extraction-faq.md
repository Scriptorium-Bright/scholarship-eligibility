# LLM Extraction FAQ

## Why This Document Exists
phase 8을 진행하면서 자주 나온 질문들을 한 번에 정리한 문서다.  
특히 아래 내용을 빠르게 다시 확인할 수 있게 만드는 것이 목적이다.

- LLM이 프로젝트의 어느 지점에 붙는지
- canonical document를 LLM에 어떻게 넘기는지
- “문서를 해체한다”는 말이 정확히 무엇을 뜻하는지
- regex 기반 추출기와 LLM 추출기가 현재 어떤 관계인지
- evidence mapping이 왜 필요한지

## One-Line Summary
이 프로젝트에서 LLM은 raw 문서를 직접 읽는 것이 아니라, 우리가 canonical scheme으로 정리한 block 문맥을 읽고 이를 구조화 규정 JSON으로 해석하는 역할을 맡는다.

## Q1. LLM은 이 프로젝트에서 어디에 붙는가?
LLM은 `extractor` 계층에 붙는다.  
즉 검색 API나 eligibility engine에 직접 붙는 것이 아니라, `canonical document -> structured rule` 구간에 들어간다.

구조는 아래와 같다.

```text
raw document
-> canonical document
-> prompt/context builder
-> LLM provider
-> structured output schema
-> ExtractedScholarshipRule
-> persistence
```

정리하면:
- 검색은 search service가 담당
- 판정은 eligibility engine이 담당
- LLM은 구조화 규정 추출만 담당

## Q2. LLM이 canonical document 객체나 파일을 직접 읽는 구조인가?
아니다.  
LLM이 파일 객체나 ORM 객체에 직접 접근해서 속성을 읽는 구조는 아니다.

실제 동작은 이렇다.

1. 우리가 raw HTML/PDF/HWP를 canonical document로 정규화한다.
2. canonical document 안의 block들을 prompt builder가 문자열로 직렬화한다.
3. LLM은 그 문자열 문맥을 읽고 구조화된 JSON을 반환한다.
4. 우리는 그 JSON을 다시 검증하고 rule/provenance로 저장한다.

즉 LLM은
- 파일을 직접 파싱하지 않고
- DB row를 직접 읽지 않고
- 우리가 만든 text context를 보고 의미를 해석한다.

## Q3. canonical document 전체를 그대로 LLM에 넘기는가?
그대로 넘기는 것이 아니라, **block 단위로 펼쳐서 prompt 형태로 다시 조립한 뒤 넘긴다**.

중요한 이유는 두 가지다.

### 1. 비용과 성능
canonical document 전체를 통째로 넘기면 prompt가 불필요하게 커진다.  
문서가 길어질수록 latency와 비용이 함께 커진다.

### 2. 근거 추적
block id가 보존되지 않으면 LLM이 “어느 문장에서 이 값을 읽었는지”를 다시 가리키기 어렵다.  
그래서 `document_id`, `block_id`, `page_number`, `text`를 같이 넘긴다.

즉 “문서 전체를 그대로 던진다”가 아니라,
**문서를 block 단위로 정리해 LLM이 근거를 다시 인용할 수 있는 형태로 만든다**가 맞다.

## Q4. 그러면 문서를 먼저 휴리스틱으로 해석해서 LLM에 넘기는 건가?
아니다.  
여기서 하는 일은 **의미 해석**이 아니라 **입력 구조화**다.

구분하면 이렇다.

### 우리가 하는 일
- raw 문서를 읽을 수 있는 형태로 정규화
- canonical block 단위로 분리
- `document_id / block_id / page_number / text`를 붙여 prompt로 직렬화
- 길면 budget 기준으로 잘라서 전달

### LLM이 하는 일
- 어떤 block이 장학명인지 해석
- 어떤 block이 GPA 조건인지 해석
- 어떤 block이 제출서류인지 해석
- 우리가 정한 output schema에 맞춰 JSON 반환

즉,
**문서 해체는 우리가 하지만 규정 해석은 LLM이 한다.**

## Q5. “해체”는 regex를 뜻하는가?
항상 그렇지는 않다.  
이 프로젝트에서 “해체”는 보통 아래 의미다.

- HTML은 DOM을 읽어 본문 block으로 정리
- PDF는 텍스트를 추출해 block으로 정리
- HWP는 preview text를 읽어 block으로 정리
- 그 결과를 canonical block 리스트로 만드는 것

즉 여기서 말하는 해체는
- 입력 구조 정리
- block 단위 분리
- prompt 직렬화
에 가깝다.

반면 **regex 기반 의미 추출**은 별도의 heuristic extractor 경로다.

정리하면:
- canonical document 해체 = 입력 포맷 정리
- regex extractor = 의미를 직접 뽑는 기존 추출기

## Q6. 우리가 정의한 scheme을 LLM이 읽고 해석하는 구조인가?
맞다.  
입력도 우리가 정의하고, 출력도 우리가 정의한다.

### 입력 측
우리는 canonical document를 아래처럼 다룬다.
- notice metadata
- `document_id`
- `block_id`
- `page_number`
- `text`

### 출력 측
LLM은 아래 schema를 따라야 한다.
- `scholarship_name`
- `summary_text`
- `qualification.gpa_min`
- `qualification.income_bracket_max`
- `qualification.grade_levels`
- `qualification.enrollment_status`
- `qualification.required_documents`
- `evidence[]`

즉
- 입력 scheme은 우리가 정하고
- 출력 schema도 우리가 정하고
- LLM은 그 사이에서 의미 해석만 담당한다.

## Q7. evidence mapping은 무엇인가?
LLM이 반환한 evidence를 우리 시스템의 provenance anchor로 바꾸는 과정이다.

예를 들어 LLM이 아래처럼 반환했다고 가정하자.

- `field_name = qualification.gpa_min`
- `document_id = 12`
- `block_id = notice-block-2`
- `quote_text = 직전학기 평점평균 3.20 이상인 재학생`

이 값을 그대로 두지 않고, 우리 시스템은 다음을 확인한다.

1. `document_id`와 `block_id`가 실제 selected block에 존재하는가
2. anchor key는 어떤 형식으로 만들 것인가
3. page number와 locator는 어떻게 저장할 것인가

이 검증과 변환을 거쳐 최종적으로 provenance anchor 형태로 저장한다.

즉 evidence mapping은
**LLM이 준 근거 정보를 우리 시스템이 저장하고 설명할 수 있는 근거 객체로 바꾸는 과정**이다.

## Q8. regex 기반 추출기는 아직 남아 있는가?
남아 있다. 그리고 지금은 남겨두는 게 맞다.

현재 구조는 아래 두 경로가 공존한다.

- heuristic extractor
- LLM extractor

heuristic extractor를 남겨두는 이유:
- baseline 비교 가능
- 외부 API 없이도 기본 동작 보장
- LLM 실패 시 fallback 후보
- phase 8.5의 hybrid fallback 기반

즉 heuristic extractor는 “낡은 코드”가 아니라,
현재는 baseline이자 fallback 자산이다.

## Q9. 지금 LLM 추출은 어디까지 구현되어 있는가?
현재 기준으로는 아래까지 왔다.

- 8.0: extractor contract 분리
- 8.1: LLM structured output schema 정의
- 8.2: prompt/context builder
- 8.3: OpenAI-compatible provider + fake provider
- 8.4: LLM extractor 통합 baseline

아직 남은 것:
- 8.5: hybrid fallback, retry, ops logging
- 8.6: evaluation set, benchmark, portfolio docs

즉 “LLM을 붙일 수 있는 구조”는 넘어섰고,  
지금은 **운영 안정성과 평가 지표를 붙이는 단계**가 남아 있다.

## Q10. 이 구조를 가장 짧게 어떻게 설명하면 좋은가?
가장 정확한 문장은 아래와 같다.

**우리가 raw 문서를 canonical block scheme으로 정리하고, LLM은 그 block 문맥을 읽어 구조화 규정을 반환하며, 최종 판정은 deterministic engine이 수행하는 구조다.**

짧게 줄이면:
- `문서 기반 구조화 추출 + 결정론적 판정 시스템`
- `canonical document를 입력으로 쓰는 LLM structured extraction pipeline`
- `문서 정규화와 규칙 기반 판정을 중심에 둔 AI extraction architecture`

## What To Avoid Saying
아래 표현은 현재 구현을 과장하게 만들 수 있다.

- “LLM이 파일을 직접 읽는다”
- “raw 문서를 그대로 LLM에 넣는다”
- “regex로 먼저 의미를 다 뽑고 LLM은 확인만 한다”
- “이미 완성된 RAG 시스템이다”
- “vector DB 기반 semantic search가 이미 붙어 있다”

## Recommended Mental Model
이 프로젝트의 LLM 경로는 아래 한 문장으로 기억하면 된다.

**우리가 문서를 읽기 좋은 구조로 정리하고, LLM은 그 구조를 해석하며, 결과 검증과 최종 판정은 다시 시스템이 책임진다.**
