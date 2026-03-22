from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.common import DocumentKind
from app.schemas.domain import StrictSchema


class ScholarshipProvenanceAnchorResponse(StrictSchema):
    """API response fragment that exposes one rule provenance anchor."""

    anchor_key: str
    block_id: str
    quote_text: str
    page_number: Optional[int] = None
    source_label: Optional[str] = None
    document_kind: Optional[DocumentKind] = None
    locator: Dict[str, Any] = Field(default_factory=dict)


class ScholarshipSearchItem(StrictSchema):
    """Search/open-list read model assembled from rule, notice, and provenance."""

    notice_id: int
    rule_id: int
    scholarship_name: str
    notice_title: str
    source_board: str
    department_name: Optional[str] = None
    notice_url: str
    published_at: datetime
    application_started_at: Optional[datetime] = None
    application_ended_at: Optional[datetime] = None
    application_status: str
    summary_text: Optional[str] = None
    qualification: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    matched_fields: List[str] = Field(default_factory=list)
    provenance: List[ScholarshipProvenanceAnchorResponse] = Field(default_factory=list)


class ScholarshipSearchResponse(StrictSchema):
    """Response returned by the scholarship keyword search API."""

    query: str
    open_only: bool = False
    count: int
    items: List[ScholarshipSearchItem]


class OpenScholarshipListResponse(StrictSchema):
    """Response returned by the current open scholarship listing API."""

    reference_time: datetime
    count: int
    items: List[ScholarshipSearchItem]
