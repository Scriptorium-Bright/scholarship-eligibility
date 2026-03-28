# Phase 8.1

## Status
- planned

## Goal
LLM이 따라야 할 structured output schema와 evidence contract를 정의한다.

## Scope
- LLM extraction response schema 추가
- field별 evidence 형식 정의
- schema validation test 추가
- quote text가 아닌 block id 기반 provenance 원칙 확정

## Changes
- `app/schemas/llm_extraction.py` 추가
- `app/schemas/__init__.py` 갱신
- `tests/unit/test_phase8_llm_schema.py` 추가
- `docs/phase-8.1.md` 추가

## How To Read This Phase
- 먼저 `app/schemas/llm_extraction.py`를 읽고 LLM이 정확히 어떤 JSON을 반환해야 하는지 확인한다.
- 다음으로 `tests/unit/test_phase8_llm_schema.py`를 보면 어떤 invalid payload를 거부할지 빠르게 파악할 수 있다.
- 마지막으로 `docs/phase-8-portfolio-rubric.md`를 같이 보면 어떤 수치를 위해 evidence contract를 강하게 잡는지 이해할 수 있다.

## File Guide
- `app/schemas/llm_extraction.py`: LLM structured output용 schema
- `app/schemas/__init__.py`: schema export 정리
- `tests/unit/test_phase8_llm_schema.py`: schema validation test

## Method Guide
### `app/schemas/llm_extraction.py`
- `LLMExtractionEvidence`: field name, block id, page number, quote text를 담는 evidence schema
- `LLMExtractionQualification`: qualification payload schema
- `LLMExtractionResponse`: scholarship rule + evidence 전체 응답 schema

### `tests/unit/test_phase8_llm_schema.py`
- valid payload parse test
- missing block id rejection test
- unsupported field name rejection test

## Importance
- high: hallucinated free-form 답변을 막고 structured extraction으로 고정
- mid: phase 8.4 provenance 매핑과 evaluation metric 정의의 기준점 확보
- low: future provider 교체 시 schema만 유지하면 되는 안정성 확보

## Problem
LLM을 바로 붙이면 자유형 텍스트 응답 때문에 parsing, validation, provenance 연결이 모두 흔들릴 수 있다.

## Solution
모델이 반환해야 할 JSON schema를 먼저 정의하고, evidence는 반드시 `block_id`를 포함하도록 강제한다.

## Result
phase 8.2와 8.3에서는 prompt와 provider를 이 schema 중심으로 구현할 수 있다.

## Tests
- planned: `pytest tests/unit/test_phase8_llm_schema.py`
- target: invalid evidence와 schema mismatch가 parser 단계에서 차단

## Portfolio Framing
LLM을 “답변기”가 아니라 “검증 가능한 structured extractor”로 제한했다는 점이 중요하다. 이 설계가 있어야 이후 accuracy와 evidence validity를 수치화할 수 있다.

## Open Risks
- schema를 너무 풍부하게 잡으면 첫 구현 난도가 급격히 올라간다.
- block id와 quote text를 동시에 강제할 경우 모델 출력 안정성이 떨어질 수 있다.

## Refactor Priorities
- high: evidence schema 필수 필드 최소화 / 성능 영향: 간접 있음
- mid: qualification schema와 기존 `ScholarshipRuleCreate` 사이 mapping helper 분리 / 성능 영향: 없음
- low: schema alias와 field description 보강 / 성능 영향: 없음

## Next Phase Impact
phase 8.2에서는 canonical block을 LLM 입력 context로 만드는 prompt/context builder를 구현한다.
