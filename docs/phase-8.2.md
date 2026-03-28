# Phase 8.2

## Status
- planned

## Goal
canonical document를 LLM structured extraction 입력으로 변환하는 prompt/context builder를 만든다.

## Scope
- canonical block serialization 규칙 정의
- block id와 page number가 보존되는 prompt builder 추가
- truncation/chunking 기본 정책 추가
- prompt builder unit test 추가

## Changes
- `app/extractors/prompt_builder.py` 추가
- `tests/unit/test_phase8_prompt_builder.py` 추가
- `docs/phase-8.2.md` 추가

## How To Read This Phase
- 먼저 `app/extractors/prompt_builder.py`를 읽고 어떤 메타데이터와 block이 LLM 입력으로 들어가는지 본다.
- 다음으로 `tests/unit/test_phase8_prompt_builder.py`를 읽어 긴 문서에서 어떤 순서와 기준으로 block이 잘리는지 확인한다.
- 마지막으로 `docs/phase-8.1.md`를 같이 보면 schema와 prompt가 어떻게 맞물리는지 이해할 수 있다.

## File Guide
- `app/extractors/prompt_builder.py`: canonical block -> LLM context 변환
- `tests/unit/test_phase8_prompt_builder.py`: prompt/context builder 테스트

## Method Guide
### `app/extractors/prompt_builder.py`
- `build_notice_context`: notice title, summary, application window, canonical blocks를 하나의 extraction context로 조립
- `serialize_block`: block id와 page number를 포함한 line serialization
- `truncate_blocks`: token/character budget에 맞춰 우선순위 기반으로 block 집합 축소

### `tests/unit/test_phase8_prompt_builder.py`
- block ordering 보존 test
- page number serialization test
- truncation budget test

## Importance
- high: LLM이 근거와 함께 안정적으로 추출하도록 만드는 실제 성능 핵심 지점
- mid: prompt compactness와 latency/cost 수치화 기반 확보
- low: 추후 여러 provider를 써도 동일 입력을 재사용할 수 있게 함

## Problem
canonical document 전체를 그대로 LLM에 넘기면 비용이 커지고, block id가 사라지면 provenance를 연결할 수 없다.

## Solution
canonical block을 `block_id / page_number / text` 중심으로 serialization하고, 긴 문서는 잘리는 규칙을 명시적으로 둔다.

## Result
phase 8.3 provider layer부터는 동일한 prompt/context builder를 통해 deterministic한 입력을 공급할 수 있다.

## Tests
- planned: `pytest tests/unit/test_phase8_prompt_builder.py`
- target: block id와 page number가 prompt에 유지되고 truncation 규칙이 재현 가능하게 동작

## Portfolio Framing
컨텍스트 엔지니어링을 추상적인 말이 아니라, canonical block 설계와 truncation 정책으로 구체화했다는 점을 강조할 수 있다.

## Open Risks
- character budget 기반 truncation은 실제 token budget과 차이가 날 수 있다.
- block 우선순위 정책이 약하면 핵심 조건문이 잘릴 수 있다.

## Refactor Priorities
- high: token estimator 또는 provider별 budget adapter 도입 / 성능 영향: 직접 있음
- mid: notice 본문과 attachment block 가중치 정책 분리 / 성능 영향: 직접 있음
- low: prompt instruction template registry 분리 / 성능 영향: 없음

## Next Phase Impact
phase 8.3에서는 실제 provider 호출 레이어와 fake provider를 구현해 prompt builder 결과를 structured output으로 연결한다.
