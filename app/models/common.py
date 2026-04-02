from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_in_seoul


class TimestampMixin:
    """시간에 따라 갱신되는 엔티티들이 공통으로 쓰는 timestamp 컬럼입니다."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_in_seoul,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_in_seoul,
        onupdate=now_in_seoul,
        nullable=False,
    )


class DocumentKind(str, Enum):
    """정규화 단계에서 지원하는 canonical document 종류입니다."""

    NOTICE_HTML = "notice_html"
    ATTACHMENT_PDF = "attachment_pdf"
    ATTACHMENT_TEXT = "attachment_text"


class RuleStatus(str, Enum):
    """추출된 장학 규정이 가질 수 있는 생명주기 상태입니다."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
