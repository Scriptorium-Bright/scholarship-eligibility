from typing import Iterable, Optional

from app.extractors import (
    ExtractedScholarshipRule,
    HeuristicScholarshipRuleExtractor,
    StructuredRuleExtractor,
)
from app.services.rule_extraction import ScholarshipRuleExtractionService


class DummyExtractor:
    """Minimal extractor used to verify the shared phase 8 contract."""

    def extract_notice_rule(
        self,
        notice_title: str,
        canonical_documents: Iterable[object],
        application_started_at: Optional[object] = None,
        application_ended_at: Optional[object] = None,
        fallback_summary: Optional[str] = None,
    ) -> ExtractedScholarshipRule:
        return ExtractedScholarshipRule(
            scholarship_name=notice_title,
            qualification={"gpa_min": 3.0},
            provenance_anchors=[],
            source_document_id=None,
            application_started_at=None,
            application_ended_at=None,
            summary_text=fallback_summary,
        )


def test_phase8_heuristic_extractor_satisfies_structured_rule_contract():
    extractor = HeuristicScholarshipRuleExtractor()

    assert isinstance(extractor, StructuredRuleExtractor)


def test_phase8_rule_extraction_service_accepts_any_structured_rule_extractor():
    extractor = DummyExtractor()

    service = ScholarshipRuleExtractionService(extractor=extractor)

    assert service._extractor is extractor
