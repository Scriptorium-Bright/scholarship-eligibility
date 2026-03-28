# Phase 8.3

## Status
- planned

## Goal
OpenAI-compatible provider, fake provider, 설정값을 추가해 LLM structured extraction 호출 기반을 만든다.

## Scope
- provider interface 추가
- OpenAI-compatible provider 추가
- fake provider 추가
- extraction model/config settings 추가
- provider parsing test 추가

## Changes
- `app/ai/providers/base.py` 추가
- `app/ai/providers/openai_provider.py` 추가
- `app/ai/providers/fake_provider.py` 추가
- `app/ai/providers/__init__.py` 추가
- `app/core/config.py` 갱신
- `.env.example` 갱신
- `tests/unit/test_phase8_provider.py` 추가
- `docs/phase-8.3.md` 추가

## How To Read This Phase
- 먼저 `app/ai/providers/base.py`를 읽고 provider contract를 확인한다.
- 다음으로 `app/ai/providers/openai_provider.py`를 읽어 structured output 호출과 parser 연결 방식을 본다.
- `app/ai/providers/fake_provider.py`와 `tests/unit/test_phase8_provider.py`를 읽으면 외부 API 없이도 어떻게 phase 8을 검증할지 이해할 수 있다.

## File Guide
- `app/ai/providers/base.py`: provider 공용 contract
- `app/ai/providers/openai_provider.py`: 실제 structured output provider
- `app/ai/providers/fake_provider.py`: 테스트용 결정론적 provider
- `app/core/config.py`: extractor mode, model, timeout, retry 설정
- `.env.example`: phase 8 관련 환경 변수
- `tests/unit/test_phase8_provider.py`: provider/fake provider parsing 검증

## Method Guide
### `app/ai/providers/base.py`
- `StructuredOutputProvider.extract_rule`: prompt/context를 받아 schema-compatible payload 반환

### `app/ai/providers/openai_provider.py`
- `extract_rule`: model 호출, schema parsing, provider exception 정리

### `app/ai/providers/fake_provider.py`
- `extract_rule`: 고정 payload 반환

### `app/core/config.py`
- extractor mode, provider model, timeout, retry, max context budget 설정 추가

## Importance
- high: phase 8의 외부 AI layer를 application code와 분리
- mid: CI와 로컬 테스트에서 fake provider로 안정적인 검증 가능
- low: future provider 교체 비용 절감

## Problem
LLM extractor를 직접 서비스 코드에 붙이면 외부 API 의존, timeout, invalid output 처리가 얽혀 테스트와 운영이 모두 불안정해진다.

## Solution
provider 계층을 분리하고, OpenAI-compatible provider와 fake provider를 함께 둔다.

## Result
phase 8.4에서는 fake provider를 이용해 실제 LLM extractor orchestration을 먼저 안정적으로 통합할 수 있다.

## Tests
- planned: `pytest tests/unit/test_phase8_provider.py`
- target: fake provider와 OpenAI-compatible provider의 공용 contract 검증

## Portfolio Framing
모델 호출을 곧바로 business logic에 박지 않고 provider abstraction과 fake provider를 둔 점은 실무형 AI 애플리케이션 엔지니어링 포인트다.

## Open Risks
- provider 예외 계층이 너무 단순하면 retry/fallback 판단이 모호해질 수 있다.
- 설정값이 늘어나면서 local/dev/test profile 관리가 복잡해질 수 있다.

## Refactor Priorities
- high: provider error taxonomy 정리 / 성능 영향: 없음
- mid: model capability flags와 context budget adapter 분리 / 성능 영향: 간접 있음
- low: provider metrics hook 확장 포인트 추가 / 성능 영향: 없음

## Next Phase Impact
phase 8.4에서는 LLM extractor 구현체를 추가해 rule extraction service에 실제 통합한다.
