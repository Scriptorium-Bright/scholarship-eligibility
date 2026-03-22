from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Enum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.common import DocumentKind, TimestampMixin


class CanonicalDocument(TimestampMixin, Base):
    """Normalized text representation derived from a notice or attachment."""

    __tablename__ = "canonical_documents"
    __table_args__ = (
        UniqueConstraint(
            "notice_id",
            "attachment_id",
            "document_kind",
            name="uq_canonical_document_scope",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[int] = mapped_column(
        ForeignKey("scholarship_notices.id", ondelete="CASCADE"),
        nullable=False,
    )
    attachment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("notice_attachments.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_kind: Mapped[DocumentKind] = mapped_column(
        Enum(DocumentKind, native_enum=False, length=32),
        nullable=False,
    )
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_text: Mapped[str] = mapped_column(Text, nullable=False)
    blocks_json: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    notice: Mapped["ScholarshipNotice"] = relationship(back_populates="canonical_documents")
    attachment: Mapped[Optional["NoticeAttachment"]] = relationship(
        back_populates="canonical_documents",
    )
    provenance_anchors: Mapped[List["ProvenanceAnchor"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    scholarship_rules: Mapped[List["ScholarshipRule"]] = relationship(
        back_populates="document",
    )


class ProvenanceAnchor(TimestampMixin, Base):
    """Traceable anchor that points back to a canonical block."""

    __tablename__ = "provenance_anchors"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "anchor_key",
            name="uq_provenance_anchor_document_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    anchor_key: Mapped[str] = mapped_column(String(120), nullable=False)
    block_id: Mapped[str] = mapped_column(String(120), nullable=False)
    quote_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(nullable=True)
    locator_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    document: Mapped[CanonicalDocument] = relationship(back_populates="provenance_anchors")

if TYPE_CHECKING:
    from app.models.notice import NoticeAttachment, ScholarshipNotice
    from app.models.rule import ScholarshipRule
