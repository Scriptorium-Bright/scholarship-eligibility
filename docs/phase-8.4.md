# Phase 8.4

## Status
- completed

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
- `README.md` 갱신
- `docs/phase-8.4.md` 갱신
- `docs/implementation-plan.md` 갱신

## What Changed
- 기존 구조:
  - phase 8.3까지는 provider layer만 있었고, 실제 business logic은 여전히 heuristic extractor만 사용했다.
  - LLM schema와 prompt builder가 있어도 `ExtractedScholarshipRule`로 바꾸는 구현체가 없어 persistence 경로에 연결되지 않았다.
  - evidence의 `document_id`와 `block_id`가 실제 canonical block과 맞는지 검증하는 단계도 없었다.
- 이번 수정:
  - `LLMScholarshipRuleExtractor`를 추가해 prompt builder -> provider -> schema output -> extracted rule 경로를 구현했다.
  - schema qualification을 기존 deterministic decision path가 쓰는 compact qualification JSON으로 변환했다.
  - evidence를 provenance anchor로 바꾸되, selected canonical block에 없는 `document_id/block_id`는 즉시 실패하도록 검증을 추가했다.
  - `ScholarshipRuleExtractionService`가 settings 기준으로 heuristic 또는 llm extractor를 기본 선택하도록 바꿨다.
- 변경 이유:
  - “provider가 있다” 수준이 아니라 실제 extraction path가 AI 기반 구현체로 교체 가능해야 phase 8의 가치가 생기기 때문이다.
  - downstream search/eligibility를 건드리지 않고 extractor만 교체하는 구조를 완성하기 위해서다.

## Python File Breakdown
- `app/extractors/llm_scholarship_rules.py`: provider 출력과 prompt context를 받아 공용 extractor result로 매핑하는 phase 8.4 핵심 파일
- `app/extractors/__init__.py`: 새 LLM extractor를 외부 import 경계에 노출하도록 갱신한 파일
- `app/services/rule_extraction.py`: settings 기반 extractor mode 선택과 LLM extractor 기본 조립을 담당하도록 바뀐 orchestration 파일
- `tests/integration/test_phase8_llm_extractor.py`: fake provider 기준 rule/provenance persistence 성공 경로와 invalid evidence 실패 경로를 검증하는 integration 테스트 파일

## Added / Updated Methods
### `app/extractors/llm_scholarship_rules.py`
- `LLMScholarshipRuleExtractor.__init__`: provider와 prompt builder를 주입받아 extractor 인스턴스를 초기화한다.
- `LLMScholarshipRuleExtractor.extract_notice_rule`: notice metadata와 canonical document를 prompt로 만들고 provider 결과를 rule/provenance로 변환한다.
- `LLMScholarshipRuleExtractor._map_evidence_to_anchor`: evidence의 `document_id/block_id`를 검증하고 provenance anchor로 매핑한다.
- `LLMScholarshipRuleExtractor._build_qualification`: 빈 값 없는 qualification JSON으로 정리해 downstream deterministic engine이 바로 쓸 수 있게 만든다.

### `app/services/rule_extraction.py`
- `ScholarshipRuleExtractionService.__init__`: extractor를 직접 주입하지 않을 때 settings를 읽어 기본 extractor를 선택한다.
- `ScholarshipRuleExtractionService._build_default_extractor`: `heuristic` 또는 `llm` mode에 맞는 extractor 구현체를 조립한다.

### `tests/integration/test_phase8_llm_extractor.py`
- `test_phase8_llm_extractor_service_persists_rule_and_provenance`: fake provider 응답이 rule/provenance persistence까지 정상 연결되는지 검증한다.
- `test_phase8_llm_extractor_rejects_unknown_evidence_block`: provider가 존재하지 않는 block id를 반환했을 때 즉시 실패하는지 검증한다.

## How To Read This Phase
- 먼저 `app/extractors/llm_scholarship_rules.py`를 읽고 provider output이 `ExtractedScholarshipRule`과 `ExtractedProvenanceAnchor`로 어떻게 바뀌는지 본다.
- 다음으로 `app/services/rule_extraction.py`를 읽어 settings 기반 mode selection이 실제 orchestration에 어떻게 연결되는지 확인한다.
- 마지막으로 `tests/integration/test_phase8_llm_extractor.py`를 읽으면 fake provider를 이용한 persistence 성공/실패 경로를 한 번에 이해할 수 있다.

## File Guide
- `app/extractors/llm_scholarship_rules.py`: LLM 기반 structured extractor
- `app/services/rule_extraction.py`: llm extractor 통합
- `tests/integration/test_phase8_llm_extractor.py`: fake provider 기반 llm extraction integration test
- `README.md`: phase 8.4 상태와 현재 한계 설명 갱신

## Method Guide
### `app/extractors/llm_scholarship_rules.py`
- `LLMScholarshipRuleExtractor.extract_notice_rule`: prompt builder + provider + schema parser + provenance mapping orchestration
- `LLMScholarshipRuleExtractor._map_evidence_to_anchor`: evidence block id를 provenance anchor로 변환하며 selected block 유효성도 검증
- `LLMScholarshipRuleExtractor._build_qualification`: schema payload를 기존 qualification JSON으로 변환

### `app/services/rule_extraction.py`
- `ScholarshipRuleExtractionService.__init__`: extractor mode 또는 dependency injection에 따라 heuristic/llm extractor 선택
- `ScholarshipRuleExtractionService._build_default_extractor`: settings 기반 기본 extractor 조립

### `tests/integration/test_phase8_llm_extractor.py`
- `test_phase8_llm_extractor_service_persists_rule_and_provenance`: fake provider success path test
- `test_phase8_llm_extractor_rejects_unknown_evidence_block`: invalid block id rejection test

## Importance
- high: 이 단계부터 실제로 “LLM structured extraction”이 프로젝트 핵심 로직에 들어간다
- mid: downstream search/eligibility를 유지한 채 AI layer 교체를 달성
- low: 기존 heuristic extractor와 결과 비교 기반 확보

## Problem
schema와 provider만으로는 실제 business logic에 AI가 들어온 것이 아니다. 최종적으로 `ExtractedScholarshipRule`을 반환하는 extractor 구현체가 필요하다.

## Solution
LLM extractor 구현체를 추가하고, evidence block id를 provenance anchor로 변환해 기존 persistence 흐름에 그대로 연결한다.

## Result
settings를 `llm`으로 두면 실제 extraction path가 provider -> prompt builder -> extracted rule -> persistence로 닫히는 baseline이 생겼고, phase 8.5에서는 운영형 안정성을 위해 fallback, retry, logging을 붙일 수 있게 되었다.

## Tests
- executed: `pytest tests/integration/test_phase8_llm_extractor.py -q`, `python3 -m py_compile app/extractors/llm_scholarship_rules.py app/services/rule_extraction.py app/extractors/__init__.py`, `pytest -q`
- result: `2 passed`, `compile ok`, `42 passed`

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
