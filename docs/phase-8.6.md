# Phase 8.6

## Status
- planned

## Goal
LLM structured extraction의 품질과 안정성을 수치화하고, 포트폴리오용 문제/해결/결과 문장까지 닫는다.

## Scope
- gold evaluation set 정의
- baseline(heuristic) vs llm vs hybrid 비교
- accuracy, evidence validity, fallback recovery, latency 측정
- phase 8 포트폴리오 문구 정리
- README / architecture / benchmark 문서 갱신

## Changes
- `tests/fixtures/phase8_gold_set/` 추가
- `tests/integration/test_phase8_evaluation.py` 추가
- `scripts/evaluate_phase8_extraction.py` 추가
- `docs/performance-benchmark.md` 갱신
- `README.md` 갱신
- `docs/system-architecture.md` 갱신
- `docs/phase-8.6.md` 추가

## How To Read This Phase
- 먼저 `tests/fixtures/phase8_gold_set/`을 보고 어떤 공지 샘플과 기대 결과로 평가하는지 확인한다.
- 다음으로 `scripts/evaluate_phase8_extraction.py`를 읽어 baseline, llm, hybrid를 어떤 지표로 비교하는지 본다.
- 마지막으로 `docs/performance-benchmark.md`와 `docs/phase-8-portfolio-rubric.md`를 같이 보면 어떤 수치가 자소서/포트폴리오 문장으로 올라가는지 이해할 수 있다.

## File Guide
- `tests/fixtures/phase8_gold_set/`: gold evaluation samples
- `tests/integration/test_phase8_evaluation.py`: 평가 시나리오 검증
- `scripts/evaluate_phase8_extraction.py`: extraction metric 계산 스크립트
- `docs/performance-benchmark.md`: phase 8 수치와 재현 방법 정리
- `README.md`: current scope와 measured result 반영
- `docs/system-architecture.md`: llm extraction과 hybrid fallback 반영

## Method Guide
### `scripts/evaluate_phase8_extraction.py`
- `load_gold_set`: gold sample 로드
- `evaluate_mode`: heuristic / llm / hybrid 모드별 결과 수집
- `compute_field_accuracy`: qualification field exact match 계산
- `compute_evidence_validity`: block id 기반 evidence valid rate 계산
- `compute_recovery_metrics`: fallback recovery rate, invalid output rate 계산

### `tests/integration/test_phase8_evaluation.py`
- evaluation script smoke test
- gold sample metric aggregation test

## Importance
- high: phase 8 전체를 포트폴리오에서 방어 가능하게 만드는 수치 확보
- mid: 어떤 mode를 기본 운영값으로 둘지 판단 근거 확보
- low: README와 architecture를 실제 구현 상태에 맞게 동기화

## Problem
LLM extraction을 붙였다고 해도, 정확도와 근거 유효성, 실패 복구율을 수치로 말하지 못하면 포트폴리오와 면접에서 설득력이 약하다.

## Solution
gold evaluation set과 비교 스크립트를 만들고, heuristic / llm / hybrid 세 모드를 동일 기준으로 측정한다.

## Result
phase 8이 끝나면 “문제 -> 해결 -> 결과” 구조로 설명 가능한 AI extraction 개선 스토리와 수치가 확보된다.

## Tests
- planned: `pytest tests/integration/test_phase8_evaluation.py`
- target: evaluation script와 metric aggregation이 재현 가능하게 동작

## Portfolio Framing
이 단계의 핵심은 “LLM을 붙였다”가 아니라 “정규식 기반 추출의 한계를 structured extraction + provenance citation + hybrid fallback으로 개선했고, 그 결과를 수치로 검증했다”가 된다.

## Open Risks
- gold set 규모가 너무 작으면 accuracy improvement를 일반화하기 어렵다.
- 실제 API 호출 비용 때문에 evaluation repeatability가 떨어질 수 있다.

## Refactor Priorities
- high: gold set annotation 기준 문서화 / 성능 영향: 없음
- mid: evaluation script와 benchmark script 통합 여부 판단 / 성능 영향: 간접 있음
- low: 결과 리포트를 markdown 표로 자동 생성 / 성능 영향: 없음

## Next Phase Impact
phase 9.x에서는 scheduler, demo, final docs를 붙여 phase 8 결과를 시연 가능한 product story로 확장할 수 있다.
