from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_in_seoul


class TimestampMixin:
    """Shared timestamp columns for entities that are updated over time."""

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
    """Supported canonical document kinds for later normalization phases."""

    NOTICE_HTML = "notice_html"
    ATTACHMENT_PDF = "attachment_pdf"
    ATTACHMENT_TEXT = "attachment_text"


class RuleStatus(str, Enum):
    """Lifecycle states for extracted scholarship rules."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
