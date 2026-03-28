"""Schemas package."""

from app.schemas.domain import (
    CanonicalBlock,
    CanonicalDocumentUpsert,
    NoticeAttachmentUpsert,
    ProvenanceAnchorCreate,
    ScholarshipNoticeUpsert,
    ScholarshipRuleCreate,
)
from app.schemas.eligibility import (
    EligibilityCheckRequest,
    EligibilityConditionCheck,
    ScholarshipEligibilityItem,
    ScholarshipEligibilityResponse,
    StudentProfile,
)
from app.schemas.llm_extraction import (
    LLMExtractionEvidence,
    LLMExtractionQualification,
    LLMExtractionResponse,
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
    "EligibilityCheckRequest",
    "EligibilityConditionCheck",
    "LLMExtractionEvidence",
    "LLMExtractionQualification",
    "LLMExtractionResponse",
    "NoticeAttachmentUpsert",
    "OpenScholarshipListResponse",
    "ProvenanceAnchorCreate",
    "ScholarshipEligibilityItem",
    "ScholarshipEligibilityResponse",
    "ScholarshipProvenanceAnchorResponse",
    "ScholarshipNoticeUpsert",
    "ScholarshipRuleCreate",
    "ScholarshipSearchItem",
    "ScholarshipSearchResponse",
    "StudentProfile",
]
