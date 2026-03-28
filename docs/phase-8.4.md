# Phase 8.4

## Status
- planned

## Goal
LLM structured extraction 구현체를 추가하고 rule extraction service에 통합한다.

## Scope
- `LLMScholarshipRuleExtractor` 추가
- schema payload -> `ExtractedScholarshipRule` mapping 추가
- block id -> provenance anchor 변환 추가
- fake provider 기반 integration test 추가

## Changes
- `app/extractors/llm_scholarship_rules.py` 추가
- `app/extractors/__init__.py` 갱신
- `app/services/rule_extraction.py` 갱신
- `tests/integration/test_phase8_llm_extractor.py` 추가
- `docs/phase-8.4.md` 추가

## How To Read This Phase
- 먼저 `app/extractors/llm_scholarship_rules.py`를 읽고 provider 출력이 공용 extractor result로 어떻게 변환되는지 본다.
- 다음으로 `app/services/rule_extraction.py`를 읽어 extractor mode가 실제 orchestration에 어떻게 연결되는지 확인한다.
- 마지막으로 `tests/integration/test_phase8_llm_extractor.py`를 보면 fake provider 기준 end-to-end extraction이 어떻게 검증되는지 이해할 수 있다.

## File Guide
- `app/extractors/llm_scholarship_rules.py`: LLM 기반 structured extractor
- `app/services/rule_extraction.py`: llm extractor 통합
- `tests/integration/test_phase8_llm_extractor.py`: fake provider 기반 llm extraction integration test

## Method Guide
### `app/extractors/llm_scholarship_rules.py`
- `extract_notice_rule`: prompt builder + provider + schema parser + provenance mapping orchestration
- `_map_evidence_to_anchor`: evidence block id를 provenance anchor로 변환
- `_build_qualification`: schema payload를 기존 qualification JSON으로 변환

### `app/services/rule_extraction.py`
- extractor mode 또는 dependency injection에 따라 heuristic/llm extractor 선택

### `tests/integration/test_phase8_llm_extractor.py`
- fake provider success path test
- block id 기반 provenance anchor 저장 test

## Importance
- high: 이 단계부터 실제로 “LLM structured extraction”이 프로젝트 핵심 로직에 들어간다
- mid: downstream search/eligibility를 유지한 채 AI layer 교체를 달성
- low: 기존 heuristic extractor와 결과 비교 기반 확보

## Problem
schema와 provider만으로는 실제 business logic에 AI가 들어온 것이 아니다. 최종적으로 `ExtractedScholarshipRule`을 반환하는 extractor 구현체가 필요하다.

## Solution
LLM extractor 구현체를 추가하고, evidence block id를 provenance anchor로 변환해 기존 persistence 흐름에 그대로 연결한다.

## Result
phase 8.5에서는 운영형 안정성을 위해 fallback, retry, logging을 붙일 수 있다.

## Tests
- planned: `pytest tests/integration/test_phase8_llm_extractor.py`
- target: fake provider 기준 llm extraction이 rule/provenance persistence까지 닫힘

## Portfolio Framing
정규식 추출기를 LLM structured extractor로 교체하되, 최종 eligibility는 deterministic하게 유지했다는 점이 이 프로젝트의 가장 강한 AI 포인트가 된다.

## Open Risks
- evidence block id가 실제 canonical block과 어긋나면 저장은 되지만 설명 가능성이 무너진다.
- 모델이 schema는 맞추더라도 field 누락이 많을 수 있다.

## Refactor Priorities
- high: evidence mapping validation 강화 / 성능 영향: 없음
- mid: llm extraction result와 heuristic result diff helper 추가 / 성능 영향: 없음
- low: extractor mode selection을 dependency factory로 분리 / 성능 영향: 없음

## Next Phase Impact
phase 8.5에서는 LLM failure를 다루는 hybrid fallback, retry, logging을 붙여 운영형 안정성을 높인다.
