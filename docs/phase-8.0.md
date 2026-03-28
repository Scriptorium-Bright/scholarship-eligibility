# Phase 8.0

## Status
- completed

## Goal
heuristic extractor와 LLM extractor가 같은 출력 계약을 따르도록 extractor 계층을 분리한다.

## Scope
- extractor 공용 interface 도입
- heuristic extractor를 interface 구현체로 정리
- rule extraction service의 concrete dependency 제거
- phase 8 공통 테스트 진입점 준비

## Changes
- `app/extractors/base.py` 추가
- `app/extractors/__init__.py` 갱신
- `app/extractors/scholarship_rules.py` 갱신
- `app/services/rule_extraction.py` 갱신
- `tests/unit/test_phase8_extractor_contract.py` 추가
- `docs/phase-8.0.md` 추가

## How To Read This Phase
- 먼저 `app/extractors/base.py`를 읽고 phase 8 extractor contract가 무엇인지 확인한다.
- 다음으로 `app/extractors/scholarship_rules.py`를 읽어 기존 heuristic 구현이 새 contract에 어떻게 맞춰지는지 본다.
- 마지막으로 `app/services/rule_extraction.py`를 읽어 orchestrator가 concrete class 대신 interface를 어떻게 주입받는지 확인한다.

## File Guide
- `app/extractors/base.py`: structured extraction 공용 protocol 또는 abstract base
- `app/extractors/scholarship_rules.py`: heuristic extractor를 contract 구현체로 정리
- `app/services/rule_extraction.py`: extractor 주입 지점 정리
- `tests/unit/test_phase8_extractor_contract.py`: heuristic extractor와 future llm extractor가 같은 반환 계약을 지키는지 검증

## Method Guide
### `app/extractors/base.py`
- `StructuredRuleExtractor.extract_notice_rule`: canonical document를 받아 `ExtractedScholarshipRule`을 반환하는 공용 메서드

### `app/extractors/scholarship_rules.py`
- `HeuristicScholarshipRuleExtractor.extract_notice_rule`: contract 구현체로 유지

### `app/services/rule_extraction.py`
- `ScholarshipRuleExtractionService.__init__`: concrete heuristic extractor 대신 contract 타입 의존
- `ScholarshipRuleExtractionService.extract_notice`: downstream persistence는 그대로 유지

## Importance
- high: phase 8 전체가 extractor 교체만으로 흘러가게 만드는 기반
- mid: downstream search/eligibility를 안 건드리고 AI layer를 붙일 수 있는 구조 확보
- low: heuristic extractor 회귀 테스트를 더 명확히 분리

## Problem
현재 rule extraction service는 heuristic extractor concrete class에 직접 묶여 있어, LLM extractor를 끼워 넣으려면 service 코드와 테스트를 함께 흔들 가능성이 있다.

## Solution
structured extraction 결과 계약을 공용 interface로 분리하고, 기존 heuristic extractor를 그 구현체 중 하나로 정리한다.

## Result
phase 8.1부터는 LLM schema와 provider를 추가해도 search/eligibility/persistence는 그대로 둔 채 extractor만 교체할 수 있는 상태가 되었다.

## Tests
- executed: `pytest tests/unit/test_phase5_rule_extractor.py tests/unit/test_phase8_extractor_contract.py`, `pytest`
- result: `3 passed`, `30 passed`

## Portfolio Framing
AI를 붙이기 전에 먼저 추출 계층을 interface로 분리해 기존 결정 엔진과 저장 계층을 안정적으로 보호했다는 점을 말할 수 있다.

## Open Risks
- contract를 너무 넓게 잡으면 fake provider와 llm provider 모두 구현 비용이 커질 수 있다.
- dataclass와 pydantic schema 경계를 이 단계에서 혼동하면 이후 structured output parsing이 복잡해진다.

## Refactor Priorities
- high: extractor result contract를 dataclass 유지 vs pydantic 전환 여부 명확화 / 성능 영향: 간접 있음
- mid: rule extraction service 내부 persistence helper 분리 / 성능 영향: 없음
- low: heuristic extractor 내 한글 장문 docstring 정리 / 성능 영향: 없음

## Next Phase Impact
phase 8.1에서는 LLM이 따라야 할 structured output schema와 evidence contract를 정의한다.
