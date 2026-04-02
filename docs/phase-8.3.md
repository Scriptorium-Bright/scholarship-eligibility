# Phase 8.3

## Status
- completed

## Goal
OpenAI-compatible provider, fake provider, 설정값을 추가해 LLM structured extraction 호출 기반을 만든다.

## Scope
- provider interface 추가
- OpenAI-compatible provider 추가
- fake provider 추가
- extraction model/config settings 추가
- provider parsing test 추가

## Changes
- `app/ai/__init__.py` 추가
- `app/ai/providers/base.py` 추가
- `app/ai/providers/openai_provider.py` 추가
- `app/ai/providers/fake_provider.py` 추가
- `app/ai/providers/__init__.py` 추가
- `app/core/config.py` 갱신
- `.env.example` 갱신
- `tests/unit/test_phase8_provider.py` 추가
- `README.md` 갱신
- `docs/phase-8.3.md` 갱신
- `docs/implementation-plan.md` 갱신

## What Changed
- 기존 구조:
  - phase 8.2까지는 LLM schema와 prompt builder만 있었고, 실제 모델 호출 계층은 존재하지 않았다.
  - future extractor가 외부 API를 어떻게 호출하고, 테스트에서는 네트워크 없이 어떤 대체 구현을 쓸지 정해져 있지 않았다.
  - 설정값도 extractor mode와 provider 정보를 담지 않아 future LLM path를 환경 변수로 제어할 수 없었다.
- 이번 수정:
  - structured output provider 공용 contract와 예외 계층을 추가했다.
  - OpenAI-compatible chat completion endpoint를 호출하는 provider를 추가했다.
  - 외부 네트워크 없이 같은 contract를 검증할 수 있는 fake provider를 추가했다.
  - settings와 `.env.example`에 extractor mode, provider, base URL, model, timeout, max context budget을 추가했다.
  - provider factory와 unit test를 추가해 config -> provider 생성 흐름을 baseline으로 닫았다.
- 변경 이유:
  - phase 8.4에서 LLM extractor를 붙일 때 service 코드가 HTTP 세부 구현을 직접 알지 않도록 경계를 먼저 분리하기 위해서다.
  - 실모델 호출 경로와 테스트용 fake 경로를 같은 contract에 맞춰 두어, extractor 통합 전에 안정적인 baseline을 만들기 위해서다.

## Python File Breakdown
- `app/ai/__init__.py`: AI 관련 provider 레이어를 담는 새 패키지 경계
- `app/ai/providers/base.py`: provider contract와 공용 예외 타입을 정의한 파일
- `app/ai/providers/openai_provider.py`: OpenAI-compatible chat completion endpoint 호출과 structured output parsing을 담당하는 파일
- `app/ai/providers/fake_provider.py`: 네트워크 없이 schema-valid payload를 반환하는 테스트용 provider 파일
- `app/ai/providers/__init__.py`: provider export와 settings 기반 factory를 제공하는 파일
- `app/core/config.py`: extractor mode와 provider 설정값을 추가한 전역 설정 파일
- `tests/unit/test_phase8_provider.py`: fake provider, HTTP parsing, response validation, settings 연동을 검증하는 phase 8.3 전용 테스트 파일

## Added / Updated Methods
### `app/ai/providers/base.py`
- `StructuredOutputProvider.extract_rule`: prompt text를 받아 schema-valid extraction 결과를 반환해야 하는 공용 메서드 계약
- `StructuredOutputProvider.close`: provider가 소유한 네트워크 리소스를 정리하기 위한 공용 종료 계약

### `app/ai/providers/fake_provider.py`
- `FakeStructuredOutputProvider.__init__`: 고정 payload 또는 사용자 지정 payload를 schema-valid 응답으로 초기화한다.
- `FakeStructuredOutputProvider.extract_rule`: prompt를 기록하고 결정론적인 extraction 결과를 반환한다.
- `FakeStructuredOutputProvider.close`: fake provider에서는 정리할 외부 리소스가 없으므로 no-op으로 둔다.
- `FakeStructuredOutputProvider._default_payload`: baseline 테스트에 사용할 최소 유효 structured output을 만든다.

### `app/ai/providers/openai_provider.py`
- `OpenAICompatibleStructuredOutputProvider.__init__`: base URL, model, api key, timeout, client를 받아 provider 인스턴스를 초기화한다.
- `OpenAICompatibleStructuredOutputProvider.extract_rule`: chat completion endpoint를 호출하고 응답을 `LLMExtractionResponse`로 검증한다.
- `OpenAICompatibleStructuredOutputProvider.close`: provider가 내부에서 생성한 HTTP client를 정리한다.
- `OpenAICompatibleStructuredOutputProvider._build_request_payload`: JSON-only structured output 요청 payload를 조립한다.
- `OpenAICompatibleStructuredOutputProvider._build_headers`: API key 유무에 따라 provider 요청 헤더를 만든다.
- `OpenAICompatibleStructuredOutputProvider._extract_message_payload`: 첫 assistant message에서 JSON payload를 꺼낸다.
- `OpenAICompatibleStructuredOutputProvider._join_text_fragments`: content가 배열로 오는 compatible provider 응답을 하나의 텍스트로 합친다.

### `app/ai/providers/__init__.py`
- `build_structured_output_provider`: settings를 보고 fake provider 또는 OpenAI-compatible provider를 생성한다.

### `tests/unit/test_phase8_provider.py`
- `test_phase8_fake_provider_returns_schema_valid_response`: fake provider가 schema-valid 응답과 prompt 기록을 남기는지 검증한다.
- `test_phase8_openai_provider_posts_chat_completion_and_parses_response`: HTTP 요청 payload와 응답 parsing이 예상대로 동작하는지 검증한다.
- `test_phase8_openai_provider_rejects_invalid_structured_output`: schema에 맞지 않는 응답을 provider response error로 차단하는지 검증한다.
- `test_phase8_provider_factory_reads_settings`: 환경 변수 기반 settings가 provider factory와 올바르게 연결되는지 검증한다.

## How To Read This Phase
- 먼저 `app/ai/providers/base.py`를 읽고 provider contract와 예외 경계를 확인한다.
- 다음으로 `app/ai/providers/openai_provider.py`를 읽어 실제 HTTP 호출과 structured output parsing이 어떻게 연결되는지 본다.
- `app/ai/providers/fake_provider.py`와 `app/ai/providers/__init__.py`를 보면 테스트용 provider와 settings 기반 factory 흐름이 보인다.
- 마지막으로 `tests/unit/test_phase8_provider.py`를 읽으면 외부 API 없이 baseline을 어떻게 검증했는지 이해할 수 있다.

## File Guide
- `app/ai/providers/base.py`: provider 공용 contract와 예외 계층
- `app/ai/providers/openai_provider.py`: 실제 structured output provider
- `app/ai/providers/fake_provider.py`: 테스트용 결정론적 provider
- `app/ai/providers/__init__.py`: settings 기반 provider factory
- `app/core/config.py`: extractor mode, provider, model, timeout, context budget 설정
- `.env.example`: phase 8 관련 환경 변수 예시
- `tests/unit/test_phase8_provider.py`: provider/fake provider/settings 검증

## Method Guide
### `app/ai/providers/base.py`
- `StructuredOutputProvider.extract_rule`: prompt text를 받아 schema-compatible payload 반환
- `StructuredOutputProvider.close`: provider 리소스 정리

### `app/ai/providers/openai_provider.py`
- `OpenAICompatibleStructuredOutputProvider.extract_rule`: model 호출, schema parsing, provider exception 정리
- `OpenAICompatibleStructuredOutputProvider._build_request_payload`: OpenAI-compatible JSON 요청 payload 생성
- `OpenAICompatibleStructuredOutputProvider._extract_message_payload`: provider 응답에서 JSON payload 추출

### `app/ai/providers/fake_provider.py`
- `FakeStructuredOutputProvider.extract_rule`: 고정 payload 반환
- `FakeStructuredOutputProvider._default_payload`: 기본 structured output 생성

### `app/ai/providers/__init__.py`
- `build_structured_output_provider`: settings 기반 provider 선택

### `app/core/config.py`
- extractor mode, provider model, timeout, max context budget 설정 추가

## Importance
- high: phase 8의 외부 AI layer를 application code와 분리
- mid: CI와 로컬 테스트에서 fake provider로 안정적인 검증 가능
- low: future provider 교체 비용 절감

## Problem
LLM extractor를 직접 서비스 코드에 붙이면 외부 API 의존, timeout, invalid output 처리가 얽혀 테스트와 운영이 모두 불안정해진다.

## Solution
provider 계층을 분리하고, OpenAI-compatible provider와 fake provider를 함께 둔다.

## Result
phase 8.4에서는 fake provider를 이용해 실제 LLM extractor orchestration을 먼저 안정적으로 통합할 수 있게 되었고, real provider path도 business logic 바깥에서 다룰 수 있는 상태가 되었다.

## Tests
- executed: `pytest tests/unit/test_phase8_provider.py -q`, `python3 -m py_compile app/ai/providers/base.py app/ai/providers/fake_provider.py app/ai/providers/openai_provider.py app/ai/providers/__init__.py app/core/config.py`, `pytest -q`
- result: `4 passed`, `compile ok`, `40 passed`

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
