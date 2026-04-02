"""외부 공지 게시판 수집 로직을 담는 collector 패키지입니다."""

from app.collectors.sources import (
    DEFAULT_COLLECTOR_SOURCES,
    JBNU_MAIN_NOTICE_SOURCE,
    JBNU_SOFTWARE_NOTICE_SOURCE,
)
from app.collectors.types import (
    CollectedAttachment,
    CollectedNotice,
    CollectedNoticeSummary,
    CollectionRunResult,
    CollectorSource,
)

__all__ = [
    "CollectedAttachment",
    "CollectedNotice",
    "CollectedNoticeSummary",
    "CollectionRunResult",
    "CollectorSource",
    "DEFAULT_COLLECTOR_SOURCES",
    "JBNU_MAIN_NOTICE_SOURCE",
    "JBNU_SOFTWARE_NOTICE_SOURCE",
]
