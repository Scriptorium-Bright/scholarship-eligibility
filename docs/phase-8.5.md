# Phase 8.5

## Status
- completed

## Goal
LLM extraction 실패를 서비스가 감당할 수 있도록 hybrid fallback, provider retry, extraction outcome logging을 추가한다.

## Scope
- extractor mode `heuristic | llm | hybrid` 지원
- provider retry 정책 추가
- provider failure / invalid evidence mapping 시 heuristic fallback
- extraction outcome logging 추가
- fallback integration test와 retry unit test 추가

## Changes
- `app/services/rule_extraction.py` 갱신
- `app/services/extraction_logging.py` 추가
- `app/ai/providers/openai_provider.py` 갱신
- `app/ai/providers/__init__.py` 갱신
- `app/core/config.py` 갱신
- `.env.example` 갱신
- `tests/integration/test_phase8_hybrid_fallback.py` 추가
- `tests/unit/test_phase8_provider.py` 갱신
- `README.md` 갱신
- `docs/phase-8.5.md` 갱신
- `docs/implementation-plan.md` 갱신

## What Changed
- 기존 구조:
  - phase 8.4까지는 `heuristic`과 `llm` 모드만 있었고, LLM path가 실패하면 그대로 예외가 전파됐다.
  - provider는 단일 요청만 보내고 끝났기 때문에 일시적 네트워크 오류를 흡수하지 못했다.
  - extraction 결과도 성공 여부만 알 수 있을 뿐, fallback 발생 여부나 error type을 운영 로그로 남기지 못했다.
- 이번 수정:
  - `hybrid` 모드에서 LLM extractor를 먼저 시도하고, provider error나 invalid evidence mapping이 발생하면 heuristic extractor로 자동 복구하도록 바꿨다.
  - OpenAI-compatible provider에 retry 횟수 설정을 추가해 네트워크 오류와 재시도 가능한 HTTP 상태를 제한적으로 흡수하도록 했다.
  - extraction success, fallback 여부, latency, error type을 공통 포맷으로 남기는 logging helper를 추가했다.
- 변경 이유:
  - 실제 운영형 AI 서비스로 설명하려면 “LLM이 잘 될 때만 동작”하는 구조로는 부족하다.
  - phase 8.6에서 recovery rate와 failure rate를 수치화하려면 outcome log format이 먼저 필요하다.

## Python File Breakdown
- `app/services/rule_extraction.py`: extractor mode 분기, hybrid fallback orchestration, extraction outcome logging 호출을 담당하는 핵심 서비스 파일
- `app/services/extraction_logging.py`: notice 단위 추출 성공/실패/fallback 로그 포맷을 정의하는 helper 파일
- `app/ai/providers/openai_provider.py`: retry 가능한 transport failure를 제한 횟수 내에서 재시도하는 provider 구현 파일
- `app/ai/providers/__init__.py`: settings 기준 provider 생성 시 retry 설정을 주입하는 factory 파일
- `app/core/config.py`: retry 횟수와 extractor mode를 읽는 환경설정 파일
- `tests/integration/test_phase8_hybrid_fallback.py`: hybrid fallback success와 llm-only failure propagation을 검증하는 integration 테스트 파일
- `tests/unit/test_phase8_provider.py`: provider retry 동작과 settings binding을 검증하는 unit 테스트 파일

## Added / Updated Methods
### `app/services/rule_extraction.py`
- `ScholarshipRuleExtractionService.__init__`: explicit extractor 주입과 settings 기반 default/hybrid 조립을 함께 지원한다.
- `ScholarshipRuleExtractionService.extract_notice`: extractor 실행 결과를 저장하고 extraction outcome log를 남긴다.
- `ScholarshipRuleExtractionService._extract_rule`: heuristic, llm, hybrid 모드를 해석하고 fallback 여부를 결정한다.
- `ScholarshipRuleExtractionService._run_extractor`: extractor 공통 contract 호출을 한 곳으로 모은다.
- `ScholarshipRuleExtractionService._build_default_extractors`: 기본 extractor와 선택적 fallback extractor를 함께 조립한다.
- `ScholarshipRuleExtractionService._build_llm_extractor`: provider와 prompt builder를 묶어 LLM extractor를 만든다.
- `ScholarshipRuleExtractionService._label_extractor`: logging과 문서에 쓸 extractor label을 결정한다.
- `ScholarshipRuleExtractionService._log_extraction_outcome`: success, fallback, failure 결과를 공통 포맷으로 기록한다.

### `app/services/extraction_logging.py`
- `ExtractionOutcomeLog`: notice 단위 추출 결과를 직렬화 가능한 형태로 담는 dataclass
- `log_extraction_result`: success/fallback/failure에 따라 log level을 나눠 extraction outcome을 기록한다.

### `app/ai/providers/openai_provider.py`
- `OpenAICompatibleStructuredOutputProvider.__init__`: retry 횟수 설정을 받도록 갱신했다.
- `OpenAICompatibleStructuredOutputProvider.extract_rule`: retry helper를 거친 뒤 structured output validation을 수행한다.
- `OpenAICompatibleStructuredOutputProvider._post_with_retry`: provider request를 제한 횟수 내에서 재시도한다.
- `OpenAICompatibleStructuredOutputProvider._should_retry_status`: 재시도 가능한 HTTP 상태를 판별한다.

### `tests/integration/test_phase8_hybrid_fallback.py`
- `test_phase8_hybrid_mode_falls_back_when_llm_evidence_is_invalid`: invalid block id를 LLM이 반환했을 때 heuristic fallback으로 복구되는지 검증한다.
- `test_phase8_hybrid_mode_falls_back_when_provider_raises_transport_error`: provider transport failure가 나도 hybrid 모드에서 성공으로 복구되는지 검증한다.
- `test_phase8_llm_mode_still_raises_when_fallback_is_disabled`: 순수 llm 모드에서는 fallback 없이 예외가 그대로 전파되는지 검증한다.

### `tests/unit/test_phase8_provider.py`
- `test_phase8_openai_provider_retries_transient_request_error`: 첫 요청 실패 후 재시도로 성공하는지 검증한다.
- `test_phase8_provider_factory_reads_settings`: retry 설정이 environment에서 정상 바인딩되는지 검증한다.

## How To Read This Phase
- 먼저 `app/services/rule_extraction.py`를 읽고 `hybrid` 모드에서 어떤 예외가 fallback 조건이 되는지 확인한다.
- 다음으로 `app/services/extraction_logging.py`를 보면 success, fallback, failure가 어떤 형식으로 로그에 남는지 바로 알 수 있다.
- 이어서 `app/ai/providers/openai_provider.py`를 보면 provider retry 범위와 한계를 확인할 수 있다.
- 마지막으로 `tests/integration/test_phase8_hybrid_fallback.py`를 읽으면 invalid evidence, transport failure, no-fallback 세 시나리오를 한 번에 이해할 수 있다.

## File Guide
- `app/services/rule_extraction.py`: hybrid fallback orchestration
- `app/services/extraction_logging.py`: extraction outcome log helper
- `app/ai/providers/openai_provider.py`: retry 가능한 provider 구현
- `app/core/config.py`: retry 설정 추가
- `tests/integration/test_phase8_hybrid_fallback.py`: hybrid fallback integration test
- `tests/unit/test_phase8_provider.py`: provider retry test

## Method Guide
### `app/services/rule_extraction.py`
- `extract_notice`: 추출 -> 저장 -> 로그 기록 전체 orchestration
- `_extract_rule`: llm/hybrid/heuristic 모드 분기와 fallback 결정
- `_build_default_extractors`: default primary/fallback extractor 조립
- `_log_extraction_outcome`: extraction outcome log 생성

### `app/services/extraction_logging.py`
- `log_extraction_result`: success, fallback, failure를 같은 메시지 형식으로 남김

### `app/ai/providers/openai_provider.py`
- `_post_with_retry`: transport failure나 재시도 가능한 HTTP 상태를 제한 횟수 내에서 다시 시도
- `_should_retry_status`: retry 대상 HTTP 상태 판별

### `tests/integration/test_phase8_hybrid_fallback.py`
- `test_phase8_hybrid_mode_falls_back_when_llm_evidence_is_invalid`: invalid evidence fallback test
- `test_phase8_hybrid_mode_falls_back_when_provider_raises_transport_error`: provider failure fallback test
- `test_phase8_llm_mode_still_raises_when_fallback_is_disabled`: llm only failure propagation test

## Importance
- high: “LLM을 붙였다”에서 끝나지 않고 실패를 흡수하는 운영형 AI 구조를 설명할 수 있게 된다.
- mid: phase 8.6에서 recovery rate, fallback rate, failure type 분포를 수치화할 준비가 된다.
- low: 이후 batch extraction scheduler를 붙일 때도 같은 log format을 재사용할 수 있다.

## Problem
LLM extractor는 성공 경로만 보면 충분해 보이지만, 실제 운영에서는 timeout, provider failure, invalid evidence mapping이 계속 발생한다. 이 상태로는 파이프라인 전체 신뢰도가 낮고, 평가나 포트폴리오에서 “운영형 AI 서비스”라고 말하기 어렵다.

## Solution
`hybrid` 모드에서 LLM extractor를 먼저 시도하고, provider error나 invalid evidence mapping이 발생하면 heuristic extractor로 fallback한다. 동시에 provider retry를 붙여 일시적 실패를 줄이고, extraction outcome logging으로 success, fallback, failure를 같은 형식으로 남기도록 만들었다.

## Result
LLM path가 불안정해도 pipeline이 heuristic baseline으로 복구될 수 있게 되었고, 순수 llm 모드에서는 기존처럼 실패를 그대로 전파해 비교 실험도 유지된다. phase 8.6에서는 이제 accuracy뿐 아니라 fallback rate, recovery rate, latency를 함께 수치화할 수 있다.

## Tests
- executed: `pytest tests/unit/test_phase8_provider.py tests/integration/test_phase8_hybrid_fallback.py -q`, `python3 -m py_compile app/services/rule_extraction.py app/services/extraction_logging.py app/ai/providers/openai_provider.py app/core/config.py`, `pytest -q`
- result: `8 passed`, `compile ok`, `46 passed`

## Portfolio Framing
LLM extractor를 단순 연결한 것이 아니라, provider retry와 hybrid fallback으로 실패를 흡수하는 운영형 AI 파이프라인까지 설계했다는 점이 phase 8.5의 핵심 포인트다.

## Open Risks
- fallback이 자주 일어나면 실제로는 heuristic baseline에 의존하는 구조가 될 수 있다.
- retry policy는 아직 고정 횟수 기반이라 provider rate limit과 backoff 전략은 추가 여지가 남아 있다.

## Refactor Priorities
- high: fallback 대상 예외를 세분화해 evidence mapping failure와 schema failure를 분리 / 성능 영향: 없음
- mid: retry policy를 backoff 포함 정책 객체로 분리 / 성능 영향: 간접 있음
- low: extraction outcome log를 metrics sink로 내보내는 adapter 분리 / 성능 영향: 간접 있음

## Next Phase Impact
phase 8.6에서는 evaluation set을 만들고 accuracy, evidence validity, fallback rate, recovery rate, latency를 benchmark 형태로 정리한다.
