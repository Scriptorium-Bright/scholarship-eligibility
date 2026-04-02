# Phase 8.6

## Status
- completed

## Goal
LLM structured extraction의 품질과 안정성을 synthetic gold set으로 수치화하고, 포트폴리오용 문제/해결/결과 문장까지 닫는다.

## Scope
- gold evaluation set 정의
- baseline(`heuristic`) vs `llm` vs `hybrid` 비교
- field exact match, evidence validity, evidence coverage, fallback recovery, latency 측정
- phase 8 포트폴리오 문구 정리
- README / architecture / benchmark / rubric 문서 갱신

## Changes
- `tests/fixtures/phase8_gold_set/` 추가
- `scripts/evaluate_phase8_extraction.py` 추가
- `tests/integration/test_phase8_evaluation.py` 추가
- `README.md` 갱신
- `docs/system-architecture.md` 갱신
- `docs/performance-benchmark.md` 갱신
- `docs/phase-8-portfolio-rubric.md` 갱신
- `docs/implementation-plan.md` 갱신
- `docs/phase-8.6.md` 갱신

## What Changed
- 기존 구조:
  - phase 8.5까지는 heuristic, llm, hybrid 경로가 구현되어 있었지만 어떤 mode가 실제로 더 나은지 수치로 말할 수 있는 근거가 없었다.
  - README와 architecture 문서도 extraction path가 어디까지 구현됐는지 서술은 있었지만, quality와 reliability에 대한 숫자는 비어 있었다.
  - 포트폴리오 기준 문서도 “무엇을 측정할지”만 있었고, 실제 결과값은 없었다.
- 이번 수정:
  - wording variation, invalid evidence, transport error를 포함한 synthetic gold set `4건`을 만들었다.
  - fixture를 현재 DB와 extractor 경로에 실제로 적재하고 `heuristic`, `llm`, `hybrid` 세 mode를 동일 조건으로 실행하는 evaluation script를 추가했다.
  - field exact match, evidence validity, evidence coverage, fallback recovery, avg/p95 latency를 계산하도록 했다.
  - 결과 수치를 README, architecture, benchmark, portfolio rubric 문서에 반영했다.
- 변경 이유:
  - “LLM을 붙였다”는 설명만으로는 포트폴리오 설득력이 약하다.
  - synthetic fixture 기준이라도 정확도와 복구율을 재현 가능하게 수치화해야 phase 8 전체가 방어 가능해진다.

## Python File Breakdown
- `scripts/evaluate_phase8_extraction.py`: gold fixture 로드, sample seed, fixture-driven provider routing, mode별 metric 집계를 수행하는 phase 8.6 핵심 스크립트
- `tests/integration/test_phase8_evaluation.py`: evaluation script smoke test와 metric regression test를 담은 integration 테스트 파일

## Added / Updated Methods
### `scripts/evaluate_phase8_extraction.py`
- `load_gold_set`: JSON fixture 디렉터리에서 gold sample 목록을 읽는다.
- `evaluate_all_modes`: heuristic, llm, hybrid 세 mode를 한 번에 평가한다.
- `evaluate_mode`: 단일 mode에 대해 temp SQLite와 fixture-driven provider를 구성하고 sample 전체를 실행한다.
- `seed_gold_set`: gold sample을 현재 DB에 materialize한다.
- `seed_gold_sample`: notice, attachment, canonical document를 sample 단위로 적재한다.
- `materialize_provider_case`: fixture payload 안의 `document_ref`를 실제 seeded document id로 치환한다.
- `evaluate_seeded_sample`: sample 하나를 실행하고 success, field match, evidence, fallback, latency metric을 계산한다.
- `load_predicted_rule`: 저장된 rule과 provenance anchor를 읽어 metric 계산용으로 정리한다.
- `compute_field_accuracy`: gold expected와 predicted rule의 field exact match를 계산한다.
- `compute_evidence_validity`: validity와 coverage를 함께 계산한다.
- `summarize_mode`: sample 결과를 mode summary로 집계한다.
- `format_summary_markdown`: README/benchmark에 붙일 markdown 표를 생성한다.
- `temporary_database_url`: evaluation 중에만 session factory가 임시 SQLite를 바라보게 한다.

### `tests/integration/test_phase8_evaluation.py`
- `test_phase8_evaluation_loads_gold_set_and_formats_markdown`: gold fixture와 summary markdown이 생성되는지 확인한다.
- `test_phase8_evaluation_shows_hybrid_balance_between_accuracy_and_reliability`: hybrid가 heuristic/llm 대비 어떤 균형을 보이는지 regression test로 고정한다.

## How To Read This Phase
- 먼저 `tests/fixtures/phase8_gold_set/`을 보고 어떤 공지 샘플과 provider failure 시나리오를 gold set으로 삼았는지 확인한다.
- 다음으로 `scripts/evaluate_phase8_extraction.py`를 읽어 fixture를 DB에 적재하고 mode별 metric을 집계하는 흐름을 본다.
- 마지막으로 `tests/integration/test_phase8_evaluation.py`와 `docs/performance-benchmark.md`를 보면 어떤 숫자를 포트폴리오 결과로 사용할 수 있는지 바로 확인할 수 있다.

## File Guide
- `tests/fixtures/phase8_gold_set/`: standard success, wording variation, invalid evidence fallback, transport error fallback을 담은 gold fixture
- `scripts/evaluate_phase8_extraction.py`: evaluation runner
- `tests/integration/test_phase8_evaluation.py`: evaluation regression test
- `docs/performance-benchmark.md`: extraction evaluation 결과와 재현 방법
- `docs/phase-8-portfolio-rubric.md`: 상위 3개 포트폴리오 포인트와 실제 관측 수치

## Method Guide
### `scripts/evaluate_phase8_extraction.py`
- `evaluate_mode`: temp SQLite, fixture-driven provider, service execution을 한 번에 조립
- `evaluate_seeded_sample`: sample별 success, field exact match, evidence coverage, fallback 여부 계산
- `compute_field_accuracy`: gold vs predicted exact match 계산
- `compute_evidence_validity`: predicted anchor가 known block에 속하는지와 expected block coverage를 같이 계산
- `summarize_mode`: mode 단위 summary 생성

### `tests/integration/test_phase8_evaluation.py`
- `test_phase8_evaluation_loads_gold_set_and_formats_markdown`: evaluation asset smoke test
- `test_phase8_evaluation_shows_hybrid_balance_between_accuracy_and_reliability`: summary metric regression test

## Importance
- high: phase 8 전체를 포트폴리오와 면접에서 방어할 수 있는 재현 가능한 수치가 생긴다.
- mid: heuristic, llm, hybrid 중 어떤 mode를 기본 운영값으로 두는지 설명할 수 있다.
- low: README와 architecture 문서를 실제 구현/측정 상태에 맞게 동기화한다.

## Problem
LLM extraction을 도입해도 정확도와 복구율을 수치로 말하지 못하면 포트폴리오에서는 “LLM을 붙여봤다” 수준에 머문다. 특히 pure llm path와 hybrid fallback의 trade-off를 정리하지 않으면 어떤 설계 결정을 했는지 설명하기 어렵다.

## Solution
wording variation과 fallback sample을 포함한 synthetic gold set을 만들고, 같은 fixture에 대해 heuristic, llm, hybrid 세 mode를 동일한 DB/서비스 경로로 실행하는 evaluation script를 추가했다. 그 결과를 field exact match, evidence validity, evidence coverage, fallback recovery, latency로 집계했다.

## Result
synthetic gold set `4건` 기준으로 hybrid는 success rate `100.00%`, field exact match `79.17%`, evidence coverage `80.95%`, fallback recovery `100.00%`를 기록했다. heuristic는 success rate는 `100.00%`지만 field exact match가 `54.17%`였고, pure llm은 field exact match `50.00%`와 success rate `50.00%`에 머물렀다. 즉 phase 8의 핵심 결과는 “표현력과 안정성을 분리하지 않고, hybrid mode로 둘을 동시에 확보했다”가 된다.

## Tests
- executed: `pytest tests/integration/test_phase8_evaluation.py -q`, `python3 scripts/evaluate_phase8_extraction.py`, `python3 -m py_compile scripts/evaluate_phase8_extraction.py tests/integration/test_phase8_evaluation.py`, `pytest -q`
- result:
  - `2 passed`
  - evaluation summary
    - heuristic: success `100.00%`, field exact match `54.17%`, evidence coverage `57.14%`
    - llm: success `50.00%`, field exact match `50.00%`, evidence coverage `52.38%`
    - hybrid: success `100.00%`, field exact match `79.17%`, evidence coverage `80.95%`, fallback recovery `100.00%`
  - `48 passed`

## Portfolio Framing
phase 8.6의 핵심 문장은 “정규식 baseline의 한계를 LLM structured extraction과 provenance validation, hybrid fallback으로 개선했고, synthetic gold set 기준으로 exact match와 recovery rate를 수치화했다”다. 여기서 포트폴리오 메인 숫자는 hybrid의 `79.17%` exact match와 `100.00%` fallback recovery다.

## Open Risks
- 현재 평가는 fixture-driven fake provider 기준이라 실OpenAI provider 품질과 비용을 그대로 대변하지는 않는다.
- gold set이 `4건`이라 sample 다양성이 아직 충분하지 않다.

## Refactor Priorities
- high: gold set annotation 기준과 failure taxonomy를 별도 문서로 분리 / 성능 영향: 없음
- mid: evaluation summary를 markdown과 JSON artifact로 자동 저장 / 성능 영향: 없음
- low: real provider smoke evaluation path를 별도 opt-in 스크립트로 분리 / 성능 영향: 간접 있음

## Next Phase Impact
phase 9.x에서는 scheduler, demo, final docs를 붙여 phase 8의 extraction path와 평가 결과를 시연 가능한 product story로 확장할 수 있다.
