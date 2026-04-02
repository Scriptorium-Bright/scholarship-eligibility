from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.common import DocumentKind, TimestampMixin


class ScholarshipRagChunk(TimestampMixin, Base):
    """
    RAG retrieval 단계가 바로 검색할 수 있는 근거 단위 텍스트 조각을 저장하는 ORM 엔티티입니다.
    canonical block, provenance, structured rule 힌트를 한 행에 묶어 retrieval과 citation hydrate의 공통 read model로 사용합니다.
    """

    __tablename__ = "scholarship_rag_chunks"
    __table_args__ = (
        UniqueConstraint(
            "chunk_key",
            name="uq_scholarship_rag_chunk_key",
        ),
        Index("ix_scholarship_rag_chunk_notice_id", "notice_id"),
        Index("ix_scholarship_rag_chunk_document_id", "document_id"),
        Index("ix_scholarship_rag_chunk_rule_id", "rule_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[int] = mapped_column(
        ForeignKey("scholarship_notices.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scholarship_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_key: Mapped[str] = mapped_column(String(255), nullable=False)
    block_id: Mapped[str] = mapped_column(String(120), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    scholarship_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    document_kind: Mapped[DocumentKind] = mapped_column(
        Enum(DocumentKind, native_enum=False, length=32),
        nullable=False,
    )
    page_number: Mapped[Optional[int]] = mapped_column(nullable=True)
    anchor_keys_json: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    embedding_vector_json: Mapped[List[float]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    notice: Mapped["ScholarshipNotice"] = relationship(back_populates="rag_chunks")
    document: Mapped["CanonicalDocument"] = relationship(back_populates="rag_chunks")
    rule: Mapped[Optional["ScholarshipRule"]] = relationship(back_populates="rag_chunks")


if TYPE_CHECKING:
    from app.models.document import CanonicalDocument
    from app.models.notice import ScholarshipNotice
    from app.models.rule import ScholarshipRule
