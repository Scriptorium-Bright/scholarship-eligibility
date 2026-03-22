"""Schemas package."""

from app.schemas.domain import (
    CanonicalBlock,
    CanonicalDocumentUpsert,
    NoticeAttachmentUpsert,
    ProvenanceAnchorCreate,
    ScholarshipNoticeUpsert,
    ScholarshipRuleCreate,
)
from app.schemas.search import (
    OpenScholarshipListResponse,
    ScholarshipProvenanceAnchorResponse,
    ScholarshipSearchItem,
    ScholarshipSearchResponse,
)

__all__ = [
    "CanonicalBlock",
    "CanonicalDocumentUpsert",
    "NoticeAttachmentUpsert",
    "OpenScholarshipListResponse",
    "ProvenanceAnchorCreate",
    "ScholarshipProvenanceAnchorResponse",
    "ScholarshipNoticeUpsert",
    "ScholarshipRuleCreate",
    "ScholarshipSearchItem",
    "ScholarshipSearchResponse",
]
