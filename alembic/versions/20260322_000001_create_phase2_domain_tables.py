"""create phase2 domain tables

Revision ID: 20260322_000001
Revises:
Create Date: 2026-03-22 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260322_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


document_kind_enum = sa.Enum(
    "notice_html",
    "attachment_pdf",
    "attachment_text",
    name="documentkind",
    native_enum=False,
)
rule_status_enum = sa.Enum(
    "draft",
    "published",
    "archived",
    name="rulestatus",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "scholarship_notices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_board", sa.String(length=100), nullable=False),
        sa.Column("source_notice_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("notice_url", sa.String(length=500), nullable=False),
        sa.Column("department_name", sa.String(length=120), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("application_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_html_path", sa.String(length=500), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_board",
            "source_notice_id",
            name="uq_scholarship_notice_source_identity",
        ),
    )
    op.create_table(
        "notice_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notice_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("raw_storage_path", sa.String(length=500), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["notice_id"], ["scholarship_notices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notice_id", "source_url", name="uq_notice_attachment_source_url"),
    )
    op.create_table(
        "canonical_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notice_id", sa.Integer(), nullable=False),
        sa.Column("attachment_id", sa.Integer(), nullable=True),
        sa.Column("document_kind", document_kind_enum, nullable=False),
        sa.Column("source_label", sa.String(length=255), nullable=False),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("blocks_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attachment_id"], ["notice_attachments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["notice_id"], ["scholarship_notices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notice_id",
            "attachment_id",
            "document_kind",
            name="uq_canonical_document_scope",
        ),
    )
    op.create_table(
        "provenance_anchors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("anchor_key", sa.String(length=120), nullable=False),
        sa.Column("block_id", sa.String(length=120), nullable=False),
        sa.Column("quote_text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("locator_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["canonical_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "anchor_key",
            name="uq_provenance_anchor_document_key",
        ),
    )
    op.create_table(
        "scholarship_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notice_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("scholarship_name", sa.String(length=255), nullable=False),
        sa.Column("rule_version", sa.String(length=50), nullable=False),
        sa.Column("application_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("qualification_json", sa.JSON(), nullable=False),
        sa.Column("provenance_keys_json", sa.JSON(), nullable=False),
        sa.Column("status", rule_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["canonical_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["notice_id"], ["scholarship_notices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notice_id",
            "scholarship_name",
            "rule_version",
            name="uq_scholarship_rule_version",
        ),
    )


def downgrade() -> None:
    op.drop_table("scholarship_rules")
    op.drop_table("provenance_anchors")
    op.drop_table("canonical_documents")
    op.drop_table("notice_attachments")
    op.drop_table("scholarship_notices")
