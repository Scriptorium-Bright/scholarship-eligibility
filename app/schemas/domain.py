from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import DocumentKind, RuleStatus


class StrictSchema(BaseModel):
    """Base schema that rejects unknown fields in pipeline payloads."""

    model_config = ConfigDict(extra="forbid")


class CanonicalBlock(StrictSchema):
    """Single normalized text block from a notice or attachment."""

    block_id: str
    block_type: str = "paragraph"
    text: str
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NoticeAttachmentUpsert(StrictSchema):
    """Attachment payload used by repository upsert helpers."""

    source_url: str
    file_name: str
    media_type: str
    raw_storage_path: Optional[str] = None
    checksum: Optional[str] = None


class ScholarshipNoticeUpsert(StrictSchema):
    """Notice payload produced by collectors before persistence."""

    source_board: str
    source_notice_id: str
    title: str
    notice_url: str
    published_at: datetime
    department_name: Optional[str] = None
    application_started_at: Optional[datetime] = None
    application_ended_at: Optional[datetime] = None
    summary: Optional[str] = None
    raw_html_path: Optional[str] = None


class CanonicalDocumentUpsert(StrictSchema):
    """Canonical document payload produced by normalization steps."""

    notice_id: int
    attachment_id: Optional[int] = None
    document_kind: DocumentKind
    source_label: str
    canonical_text: str
    blocks: List[CanonicalBlock]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProvenanceAnchorCreate(StrictSchema):
    """Provenance pointer payload linked to canonical documents."""

    document_id: int
    anchor_key: str
    block_id: str
    quote_text: str
    page_number: Optional[int] = None
    locator: Dict[str, Any] = Field(default_factory=dict)


class ScholarshipRuleCreate(StrictSchema):
    """Structured scholarship rule payload produced by extraction steps."""

    notice_id: int
    document_id: Optional[int] = None
    scholarship_name: str
    rule_version: str = "v1"
    application_started_at: Optional[datetime] = None
    application_ended_at: Optional[datetime] = None
    summary_text: Optional[str] = None
    qualification: Dict[str, Any] = Field(default_factory=dict)
    provenance_keys: List[str] = Field(default_factory=list)
    status: RuleStatus = RuleStatus.PUBLISHED
