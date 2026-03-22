from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import now_in_seoul
from app.models.base import Base
from app.models.common import TimestampMixin


class ScholarshipNotice(TimestampMixin, Base):
    """Raw notice metadata collected from JBNU boards."""

    __tablename__ = "scholarship_notices"
    __table_args__ = (
        UniqueConstraint(
            "source_board",
            "source_notice_id",
            name="uq_scholarship_notice_source_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_board: Mapped[str] = mapped_column(String(100), nullable=False)
    source_notice_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notice_url: Mapped[str] = mapped_column(String(500), nullable=False)
    department_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    application_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    application_ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_html_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_in_seoul,
        nullable=False,
    )

    attachments: Mapped[List["NoticeAttachment"]] = relationship(
        back_populates="notice",
        cascade="all, delete-orphan",
    )
    canonical_documents: Mapped[List["CanonicalDocument"]] = relationship(
        back_populates="notice",
        cascade="all, delete-orphan",
    )
    scholarship_rules: Mapped[List["ScholarshipRule"]] = relationship(
        back_populates="notice",
        cascade="all, delete-orphan",
    )


class NoticeAttachment(TimestampMixin, Base):
    """Attachment metadata linked to a collected notice."""

    __tablename__ = "notice_attachments"
    __table_args__ = (
        UniqueConstraint(
            "notice_id",
            "source_url",
            name="uq_notice_attachment_source_url",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[int] = mapped_column(
        ForeignKey("scholarship_notices.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    notice: Mapped[ScholarshipNotice] = relationship(back_populates="attachments")
    canonical_documents: Mapped[List["CanonicalDocument"]] = relationship(
        back_populates="attachment",
    )

if TYPE_CHECKING:
    from app.models.document import CanonicalDocument
    from app.models.rule import ScholarshipRule
