# Phase 8.2

## Status
- completed

## Goal
canonical document를 LLM structured extraction 입력으로 변환하는 prompt/context builder를 만든다.

## Scope
- canonical block serialization 규칙 정의
- block id와 page number가 보존되는 prompt builder 추가
- truncation/chunking 기본 정책 추가
- prompt builder unit test 추가

## Changes
- `app/extractors/prompt_builder.py` 추가
- `app/extractors/__init__.py` 갱신
- `tests/unit/test_phase8_prompt_builder.py` 추가
- `docs/phase-8.2.md` 갱신

## What Changed
- 기존 구조:
  - canonical document는 DB와 heuristic extractor 내부에서만 소비되었고, LLM provider에 넘길 입력 포맷이 없었다.
  - 어떤 block을 어떤 순서로 포함할지, 긴 문서를 어디서 자를지에 대한 공통 규칙이 없었다.
- 이번 수정:
  - canonical block을 `document_id`, `source_label`, `document_kind`, `block_id`, `page_number`, `text`로 평탄화하는 prompt builder를 추가했다.
  - notice metadata와 block serialization을 하나의 prompt text로 조립하는 context builder를 추가했다.
  - character budget 기반 truncation 규칙을 넣고, block 순서 보존과 page number serialization을 테스트로 고정했다.
- 변경 이유:
  - future provider가 어떤 모델이든 동일한 입력을 받게 해 extraction 결과 비교가 가능하도록 만들기 위해서다.
  - provenance를 block id 단위로 매핑하려면 prompt에서 그 식별자가 절대 사라지지 않아야 하기 때문이다.

## Python File Breakdown
- `app/extractors/prompt_builder.py`: canonical document를 LLM extraction용 deterministic prompt context로 변환하는 파일
- `app/extractors/__init__.py`: extractor public export에 prompt builder 관련 타입을 추가한 파일
- `tests/unit/test_phase8_prompt_builder.py`: block ordering, page number, truncation 정책을 검증하는 phase 8.2 전용 테스트 파일

## Added / Updated Methods
### `app/extractors/prompt_builder.py`
- `NoticeExtractionPromptBuilder.__init__`: prompt 조립 시 사용할 최대 문자 수 budget을 설정한다.
- `NoticeExtractionPromptBuilder.build_notice_context`: notice 메타데이터와 canonical block을 하나의 extraction prompt로 조립한다.
- `NoticeExtractionPromptBuilder.serialize_block`: document id와 block id를 잃지 않는 block 단위 serialization 문자열을 만든다.
- `NoticeExtractionPromptBuilder.truncate_blocks`: source order를 유지하면서 deterministic character budget을 강제한다.
- `NoticeExtractionPromptBuilder._flatten_documents`: notice 본문과 첨부 문서를 하나의 ordered block list로 평탄화한다.

### `tests/unit/test_phase8_prompt_builder.py`
- `test_phase8_prompt_builder_preserves_block_order_in_context`: prompt text와 selected block 목록에서 source order가 유지되는지 검증한다.
- `test_phase8_prompt_builder_serializes_page_numbers`: page number와 document id가 prompt에 그대로 남는지 검증한다.
- `test_phase8_prompt_builder_truncates_to_character_budget`: 예산을 넘는 block이 deterministic하게 잘리는지 검증한다.

## How To Read This Phase
- 먼저 `app/extractors/prompt_builder.py`를 읽고 canonical document가 어떤 prompt text로 바뀌는지 본다.
- 다음으로 `tests/unit/test_phase8_prompt_builder.py`를 읽어 순서 보존, page number 유지, truncation 규칙이 어떻게 검증되는지 확인한다.
- 마지막으로 `docs/phase-8.1.md`를 같이 보면 schema contract와 prompt input contract가 어떻게 연결되는지 이해할 수 있다.

## File Guide
- `app/extractors/prompt_builder.py`: canonical block -> LLM extraction context 변환
- `app/extractors/__init__.py`: prompt builder 관련 타입 export
- `tests/unit/test_phase8_prompt_builder.py`: prompt/context builder 테스트

## Method Guide
### `app/extractors/prompt_builder.py`
- `NoticeExtractionPromptBuilder.__init__`: 최대 문자 수 budget을 받아 builder 인스턴스를 초기화한다.
- `NoticeExtractionPromptBuilder.build_notice_context`: notice metadata, canonical block, truncation 결과를 묶어 최종 prompt context를 만든다.
- `NoticeExtractionPromptBuilder.serialize_block`: block을 evidence-friendly line string으로 직렬화한다.
- `NoticeExtractionPromptBuilder.truncate_blocks`: character budget 안에서 block 순서를 유지하며 선택할 block만 남긴다.
- `NoticeExtractionPromptBuilder._flatten_documents`: 여러 canonical document의 block을 하나의 ordered list로 변환한다.

### `tests/unit/test_phase8_prompt_builder.py`
- `test_phase8_prompt_builder_preserves_block_order_in_context`: block ordering 보존 검증
- `test_phase8_prompt_builder_serializes_page_numbers`: page number serialization 검증
- `test_phase8_prompt_builder_truncates_to_character_budget`: truncation budget 검증

## Importance
- high: LLM이 근거와 함께 안정적으로 추출하도록 만드는 실제 성능 핵심 지점
- mid: prompt compactness와 latency/cost 수치화 기반 확보
- low: 추후 여러 provider를 써도 동일 입력을 재사용할 수 있게 함

## Problem
canonical document 전체를 그대로 LLM에 넘기면 비용이 커지고, block id가 사라지면 provenance를 연결할 수 없다.

## Solution
canonical block을 `block_id / page_number / text` 중심으로 serialization하고, 긴 문서는 잘리는 규칙을 명시적으로 둔다.

## Result
phase 8.3 provider layer부터는 동일한 prompt/context builder를 통해 deterministic한 입력을 공급할 수 있고, 이후 latency와 evidence valid rate 비교도 같은 입력 기준으로 측정할 수 있게 되었다.

## Tests
- executed: `pytest tests/unit/test_phase8_prompt_builder.py -q`, `pytest -q`
- result: `3 passed`, `36 passed`

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
