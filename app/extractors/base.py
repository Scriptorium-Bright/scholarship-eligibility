from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, Optional, Protocol, runtime_checkable

from app.models import RuleStatus


@dataclass(frozen=True)
class ExtractedProvenanceAnchor:
    """어떤 추출기 구현체든 공통으로 만드는 구조화 근거 후보입니다."""

    document_id: int
    anchor_key: str
    block_id: str
    quote_text: str
    page_number: Optional[int] = None
    locator: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractedScholarshipRule:
    """heuristic과 LLM 추출기가 함께 쓰는 구조화 장학 규정 계약입니다."""

    scholarship_name: str
    qualification: Dict[str, object]
    provenance_anchors: list[ExtractedProvenanceAnchor]
    source_document_id: Optional[int]
    application_started_at: Optional[datetime]
    application_ended_at: Optional[datetime]
    summary_text: Optional[str]
    status: RuleStatus = RuleStatus.PUBLISHED


@runtime_checkable
class StructuredRuleExtractor(Protocol):
    """phase 8 구현체들이 공통으로 만족해야 하는 추출 계약입니다."""

    def extract_notice_rule(
        self,
        notice_title: str,
        canonical_documents: Iterable[object],
        application_started_at: Optional[datetime] = None,
        application_ended_at: Optional[datetime] = None,
        fallback_summary: Optional[str] = None,
    ) -> ExtractedScholarshipRule:
        """정규화 공지 문서 집합에서 구조화된 장학 규정 한 건을 추출합니다."""
