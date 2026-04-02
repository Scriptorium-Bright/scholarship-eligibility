from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionOutcomeLog:
    """공지 단위 추출 결과를 운영 로그에 남길 때 쓰는 직렬화 가능한 payload입니다."""

    notice_id: int
    requested_mode: str
    extractor_used: str
    success: bool
    fallback_used: bool
    latency_ms: float
    error_type: Optional[str] = None
    error_message: Optional[str] = None


def log_extraction_result(outcome: ExtractionOutcomeLog) -> None:
    """
    추출 성공, fallback 발생, 최종 실패를 같은 형식으로 남겨 후속 benchmark와 운영 분석에 재사용합니다.
    성공 여부에 따라 info, warning, error 레벨을 나눠 phase 8.6에서 recovery rate를 집계하기 쉽게 만듭니다.
    """

    log_function = logger.info
    if not outcome.success:
        log_function = logger.error
    elif outcome.fallback_used:
        log_function = logger.warning

    log_function(
        (
            "rule extraction outcome "
            "notice_id=%s requested_mode=%s extractor_used=%s success=%s "
            "fallback_used=%s latency_ms=%.2f error_type=%s error_message=%s"
        ),
        outcome.notice_id,
        outcome.requested_mode,
        outcome.extractor_used,
        outcome.success,
        outcome.fallback_used,
        outcome.latency_ms,
        outcome.error_type or "-",
        outcome.error_message or "-",
    )
