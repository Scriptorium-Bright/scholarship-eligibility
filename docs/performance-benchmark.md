# Performance Benchmark

## Goal
search/eligibility read path가 published rule 수와 provenance anchor 수가 늘어날 때 얼마나 무거워지는지 확인하고, 응답 직전에만 provenance를 hydrate하도록 바꾼 뒤 전후 차이를 측정했다.

## What Was Measured
- 대상 API: `GET /api/v1/scholarships/search?query=장학금&limit=10`
- 비교 대상:
  - baseline: 모든 rule의 provenance anchor를 먼저 조립하던 구조
  - optimized: 후보 탐색 단계에서는 provenance를 비우고, 정렬/limit 이후 최종 응답 item에만 provenance를 hydrate하는 구조
- baseline 기준 코드: commit `bc948e6`

## Benchmark Dataset
성능 측정용 synthetic data는 [perf/seed_perf_data.py](/Users/jeonjeonghyeon/studyCollection/jbnu-scholarship-eligibility/perf/seed_perf_data.py#L18)로 생성했다.

- published scholarship rules: `1,500`
- provenance anchors per rule: `8`
- total provenance anchors: `12,000`
- database: SQLite
- reference date: `2026-03-22 12:00 Asia/Seoul`

seed command:

```bash
python3 perf/seed_perf_data.py --count 1500 --anchors 8 --database-path /tmp/jbnu-scholarship-perf.sqlite3
```

## Load Scenario
부하 스크립트는 [perf/k6_scholarships.js](/Users/jeonjeonghyeon/studyCollection/jbnu-scholarship-eligibility/perf/k6_scholarships.js#L4)를 사용했다.

- scenario: `search`
- VUs: `10`
- iterations: `60`
- query: `장학금`
- limit: `10`

example command:

```bash
K6_WEB_DASHBOARD=false BASE_URL=http://127.0.0.1:18080 SCENARIO=search VUS=10 ITERATIONS=60 k6 run perf/k6_scholarships.js
```

## Optimization Summary
변경 핵심은 “후보 전체에 대해 provenance를 먼저 조립하지 않는다”는 점이다.

### Before
- published rule 조회 시 `notice + document + provenance_anchors`를 모두 eager load
- 검색 후보를 점수 계산하기 전에 `ScholarshipSearchItem.provenance`를 매번 조립
- 최종적으로는 상위 `limit`개만 응답해도, 중간 후보 전체가 provenance 비용을 부담

### After
- search/open/eligibility 후보 탐색 단계에서는 provenance anchor preload를 끔
- lexical scoring은 `canonical_text`를 직접 사용
- 정렬과 `limit` 이후, 최종 응답 item에 대해서만 provenance를 hydrate

관련 코드:
- [app/repositories/rule_repository.py](/Users/jeonjeonghyeon/studyCollection/jbnu-scholarship-eligibility/app/repositories/rule_repository.py#L18)
- [app/services/search.py](/Users/jeonjeonghyeon/studyCollection/jbnu-scholarship-eligibility/app/services/search.py#L24)
- [app/services/eligibility.py](/Users/jeonjeonghyeon/studyCollection/jbnu-scholarship-eligibility/app/services/eligibility.py#L272)

## Results
동일 데이터셋, 동일 k6 시나리오로 baseline과 optimized를 비교했다.

| Metric | Baseline | Optimized | Improvement |
| --- | ---: | ---: | ---: |
| avg latency | 11.13s | 4.20s | 62.28% |
| p95 latency | 12.66s | 5.07s | 59.96% |
| throughput | 0.876 req/s | 2.331 req/s | 165.94% |
| error rate | 0.00% | 0.00% | - |

## Interpretation
- 이 프로젝트의 read path 병목은 “검색 후보 전체에 대한 provenance 조립”이었다.
- 문서 기반 검색 서비스라도, 근거를 항상 전부 응답 모델로 만들면 candidate set이 커질수록 latency가 급격히 늘어난다.
- provenance는 최종 응답 품질에는 중요하지만, 모든 중간 후보에 대해 미리 붙일 필요는 없었다.
- 결과적으로 “검색 품질을 유지하면서 응답 비용을 줄이는 구조 분리”가 성능 개선으로 이어졌다.

## Reproduction Notes
- 이 수치는 로컬 환경, SQLite, synthetic benchmark dataset 기준이다.
- 절대 수치보다 “동일 조건에서 전후 비교했을 때 어느 병목이 개선됐는가”를 보는 용도로 해석하는 것이 맞다.
- semantic search, PostgreSQL, pgvector가 붙는 운영형 구조에서는 다시 측정이 필요하다.

## Phase 8 Extraction Evaluation
phase 8.6에서는 search read path 성능과 별개로, LLM structured extraction과 hybrid fallback의 품질/안정성을 synthetic gold set으로 평가했다.

### Evaluation Dataset
- gold samples: `4`
- 구성:
  - standard success sample `1건`
  - wording variation success sample `1건`
  - invalid evidence fallback sample `1건`
  - transport error fallback sample `1건`
- 실행 환경:
  - database: SQLite
  - provider: fixture-driven fake provider
  - modes: `heuristic`, `llm`, `hybrid`

평가 스크립트는 [scripts/evaluate_phase8_extraction.py](/Users/jeonjeonghyeon/studyCollection/jbnu-scholarship-eligibility/scripts/evaluate_phase8_extraction.py#L1)를 사용했다.

example command:

```bash
python3 scripts/evaluate_phase8_extraction.py
```

### Metrics
- extraction success rate
- field exact match rate
- evidence validity rate
- evidence coverage rate
- fallback recovery rate
- average / p95 latency

### Results

| Mode | Success Rate | Field Exact Match | Evidence Validity | Evidence Coverage | Fallback Recovery | Avg Latency | p95 Latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristic | 100.00% | 54.17% | 100.00% | 57.14% | 0.00% | 4.25ms | 8.04ms |
| llm | 50.00% | 50.00% | 100.00% | 52.38% | 0.00% | 2.61ms | 5.48ms |
| hybrid | 100.00% | 79.17% | 100.00% | 80.95% | 100.00% | 3.06ms | 4.54ms |

### Interpretation
- pure llm mode는 success sample에서 field-level quality가 나쁘지 않았지만, invalid evidence와 transport error sample에서 그대로 실패해 success rate가 `50.00%`에 머물렀다.
- heuristic mode는 안정성은 높았지만 wording variation sample에서 학년, 학적, 제출서류 추출이 약해 field exact match가 `54.17%`였다.
- hybrid mode는 llm success sample의 표현력과 heuristic fallback의 안정성을 같이 가져가면서 field exact match를 `79.17%`까지 끌어올렸고, fallback recovery rate `100.00%`를 기록했다.
- evidence validity는 성공한 모든 mode에서 `100.00%`였지만, expected block 대비 coverage는 hybrid가 `80.95%`로 가장 높았다.

### Portfolio Notes
- 포트폴리오에서는 “LLM을 붙였다”보다 “정규식 baseline 위에 structured extraction과 hybrid fallback을 얹고 synthetic gold set으로 정확도와 recovery를 수치화했다”가 핵심 문장이다.
- 다만 이 수치는 실OpenAI provider가 아니라 fake provider와 gold fixture 기준이므로, production accuracy나 일반화된 성능처럼 주장하면 안 된다.
