# Phase 8.5

## Status
- planned

## Goal
LLM extraction 실패를 감당할 수 있도록 hybrid fallback, retry, extraction logging을 추가한다.

## Scope
- extractor mode `heuristic | llm | hybrid` 지원
- provider retry 및 timeout 정책 추가
- invalid schema / provider failure 시 heuristic fallback
- extraction outcome logging 추가
- fallback integration test 추가

## Changes
- `app/services/rule_extraction.py` 갱신
- `app/core/config.py` 갱신
- `app/services/extraction_logging.py` 추가
- `tests/integration/test_phase8_hybrid_fallback.py` 추가
- `docs/phase-8.5.md` 추가

## How To Read This Phase
- 먼저 `app/services/rule_extraction.py`를 읽고 `llm`, `hybrid`, `heuristic` 세 모드의 분기점을 확인한다.
- 다음으로 `app/services/extraction_logging.py`를 보면 어떤 실패/성공 메타데이터를 남길지 알 수 있다.
- 마지막으로 `tests/integration/test_phase8_hybrid_fallback.py`를 읽어 invalid output이나 provider failure가 어떻게 복구되는지 본다.

## File Guide
- `app/services/rule_extraction.py`: mode 선택, fallback orchestration
- `app/services/extraction_logging.py`: extraction outcome 기록 helper
- `app/core/config.py`: retry, timeout, extractor mode 설정
- `tests/integration/test_phase8_hybrid_fallback.py`: hybrid fallback integration test

## Method Guide
### `app/services/rule_extraction.py`
- `extract_notice`: llm call -> validate -> fallback 결정
- `_should_fallback`: provider failure와 invalid schema를 heuristic fallback 조건으로 변환

### `app/services/extraction_logging.py`
- `log_extraction_result`: extractor mode, latency, fallback 여부, success 여부 기록

### `tests/integration/test_phase8_hybrid_fallback.py`
- invalid schema fallback test
- provider exception fallback test
- pure llm mode failure propagation test

## Importance
- high: 실제 서비스형 AI 구조로 설명하려면 fallback과 failure handling이 필수
- mid: evaluation 단계에서 recovery rate와 invalid output rate를 수치화할 수 있음
- low: 향후 batch extraction 운영 로그 확장 포인트 확보

## Problem
LLM extraction은 성공 path만 보면 멋있지만, 실제로는 timeout과 invalid output이 생기므로 그대로 운영에 두기 어렵다.

## Solution
hybrid mode에서 schema validation과 provider failure를 감지해 heuristic fallback으로 복구하고, extraction 결과를 로그로 남긴다.

## Result
phase 8.6에서는 accuracy뿐 아니라 failure recovery rate와 latency까지 함께 평가할 수 있다.

## Tests
- planned: `pytest tests/integration/test_phase8_hybrid_fallback.py`
- target: invalid output과 provider failure 상황에서도 pipeline success 보장

## Portfolio Framing
LLM을 단순히 붙인 것이 아니라 실패를 흡수하는 hybrid fallback 구조까지 설계했다는 점이 운영형 AI 애플리케이션 포인트다.

## Open Risks
- fallback이 너무 자주 일어나면 실제로는 heuristic 시스템과 차별점이 약해질 수 있다.
- extraction logging 저장 위치를 빨리 결정하지 않으면 phase 8.6 수치 수집이 분산될 수 있다.

## Refactor Priorities
- high: extraction outcome log schema 명확화 / 성능 영향: 없음
- mid: retry policy와 fallback policy 분리 / 성능 영향: 간접 있음
- low: notice 단위 batch runner 분리 / 성능 영향: 간접 있음

## Next Phase Impact
phase 8.6에서는 evaluation set과 benchmark를 만들어 accuracy, evidence validity, recovery rate, latency를 수치화한다.
