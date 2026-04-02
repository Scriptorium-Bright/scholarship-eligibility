"""create phase9 rag chunk table

Revision ID: 20260402_000001
Revises: 20260322_000001
Create Date: 2026-04-02 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260402_000001"
down_revision: Union[str, None] = "20260322_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


document_kind_enum = sa.Enum(
    "notice_html",
    "attachment_pdf",
    "attachment_text",
    name="documentkind",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "scholarship_rag_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notice_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("chunk_key", sa.String(length=255), nullable=False),
        sa.Column("block_id", sa.String(length=120), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("scholarship_name", sa.String(length=255), nullable=True),
        sa.Column("source_label", sa.String(length=255), nullable=False),
        sa.Column("document_kind", document_kind_enum, nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("anchor_keys_json", sa.JSON(), nullable=False),
        sa.Column("embedding_vector_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["canonical_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notice_id"], ["scholarship_notices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["scholarship_rules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_key", name="uq_scholarship_rag_chunk_key"),
    )
    op.create_index(
        "ix_scholarship_rag_chunk_notice_id",
        "scholarship_rag_chunks",
        ["notice_id"],
    )
    op.create_index(
        "ix_scholarship_rag_chunk_document_id",
        "scholarship_rag_chunks",
        ["document_id"],
    )
    op.create_index(
        "ix_scholarship_rag_chunk_rule_id",
        "scholarship_rag_chunks",
        ["rule_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scholarship_rag_chunk_rule_id", table_name="scholarship_rag_chunks")
    op.drop_index("ix_scholarship_rag_chunk_document_id", table_name="scholarship_rag_chunks")
    op.drop_index("ix_scholarship_rag_chunk_notice_id", table_name="scholarship_rag_chunks")
    op.drop_table("scholarship_rag_chunks")
