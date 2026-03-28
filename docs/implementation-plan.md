# Implementation Plan

## Delivery Rules
- phase는 `n.x` 단위로 구현한다.
- 각 phase `n.x`는 기능 구현 커밋 후 테스트/문서 커밋 순서로 진행한다.
- 커밋 메시지는 한글 서술형으로만 작성하고, `feat`, `test`, `phase n.x` 같은 prefix를 붙이지 않는다.
- 각 phase `n.x` 종료 시 실행한 테스트와 결과를 `docs/phase-n.x.md`에 남긴다.
- 각 phase `n.x` 문서에는 `Refactor Priorities`를 두고 `high / mid / low`로 정리한다.
- `Refactor Priorities` 각 항목에는 `성능 영향: 직접 있음 / 간접 있음 / 없음` 중 하나를 함께 적는다.
- phase를 시작하기 전에 목표, 수치화 후보, 포트폴리오 관점의 문제/해결/결과 구조를 먼저 문서로 확정한다.

## Phase Summary
- 1.0 문서 구조와 요구사항 정리
- 1.1 FastAPI, SQLAlchemy, Alembic, pytest 기반 부트스트랩
- 1.2 Docker Compose, PostgreSQL + pgvector, 환경설정 표준화
- 2.x 도메인 모델, 마이그레이션, repository
- 3.x collector
- 4.x raw storage, HTML/PDF normalization
- 5.x rule extraction, provenance
- 6.x hybrid search and APIs
- 7.x eligibility engine and answer builder
- 8.0 extractor contract 분리
- 8.1 LLM structured output schema와 evidence contract
- 8.2 prompt/context builder
- 8.3 OpenAI-compatible provider, fake provider, config
- 8.4 LLM extractor 통합
- 8.5 hybrid fallback, retry, extraction ops logging
- 8.6 evaluation set, benchmark, portfolio docs
- 9.x scheduler, demo, final docs

## Current Progress
- completed: 1.0, 1.1, 1.2, 2.0, 2.1, 3.0, 3.1, 4.0, 4.1, 4.2, 5.0, 5.1, 6.0, 6.1, 7.0, 7.1, 8.0
- next: 8.1 LLM structured output schema와 evidence contract
