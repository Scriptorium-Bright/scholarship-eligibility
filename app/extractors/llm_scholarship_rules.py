from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional

from app.ai.providers import StructuredOutputProvider
from app.extractors.base import (
    ExtractedProvenanceAnchor,
    ExtractedScholarshipRule,
    StructuredRuleExtractor,
)
from app.extractors.prompt_builder import ExtractionPromptBlock, NoticeExtractionPromptBuilder
from app.models import RuleStatus
from app.schemas import LLMExtractionEvidence, LLMExtractionQualification


class LLMScholarshipRuleExtractor(StructuredRuleExtractor):
    """Convert LLM structured output into the shared scholarship rule contract."""

    def __init__(
        self,
        *,
        provider: StructuredOutputProvider,
        prompt_builder: Optional[NoticeExtractionPromptBuilder] = None,
    ):
        self._provider = provider
        self._prompt_builder = prompt_builder or NoticeExtractionPromptBuilder()

    def extract_notice_rule(
        self,
        notice_title: str,
        canonical_documents: Iterable[object],
        application_started_at: Optional[datetime] = None,
        application_ended_at: Optional[datetime] = None,
        fallback_summary: Optional[str] = None,
    ) -> ExtractedScholarshipRule:
        """Build one prompt, call the provider, and map the response back to rule + provenance."""

        prompt_context = self._prompt_builder.build_notice_context(
            notice_title=notice_title,
            canonical_documents=canonical_documents,
            fallback_summary=fallback_summary,
            application_started_at=application_started_at,
            application_ended_at=application_ended_at,
        )
        if not prompt_context.selected_blocks:
            raise ValueError("No canonical blocks available for LLM extraction")

        provider_response = self._provider.extract_rule(prompt_text=prompt_context.prompt_text)
        qualification = self._build_qualification(provider_response.qualification)
        if not qualification:
            raise ValueError("No scholarship qualification fields could be extracted from LLM output")

        block_lookup = {
            (block.document_id, block.block_id): block for block in prompt_context.selected_blocks
        }
        provenance_anchors = [
            self._map_evidence_to_anchor(evidence, block_lookup, index)
            for index, evidence in enumerate(provider_response.evidence, start=1)
        ]

        source_document_id = None
        if provenance_anchors:
            source_document_id = provenance_anchors[0].document_id
        elif prompt_context.selected_blocks:
            source_document_id = prompt_context.selected_blocks[0].document_id

        return ExtractedScholarshipRule(
            scholarship_name=provider_response.scholarship_name.strip(),
            qualification=qualification,
            provenance_anchors=provenance_anchors,
            source_document_id=source_document_id,
            application_started_at=application_started_at,
            application_ended_at=application_ended_at,
            summary_text=provider_response.summary_text or fallback_summary or notice_title,
            status=RuleStatus.PUBLISHED,
        )

    def _map_evidence_to_anchor(
        self,
        evidence: LLMExtractionEvidence,
        block_lookup: Dict[tuple[int, str], ExtractionPromptBlock],
        index: int,
    ) -> ExtractedProvenanceAnchor:
        """Validate one evidence pointer against selected blocks and map it to provenance storage."""

        lookup_key = (evidence.document_id, evidence.block_id)
        block = block_lookup.get(lookup_key)
        if block is None:
            raise ValueError(
                "LLM evidence references unknown canonical block: {0}:{1}".format(
                    evidence.document_id,
                    evidence.block_id,
                )
            )

        field_slug = evidence.field_name.replace(".", "-")
        return ExtractedProvenanceAnchor(
            document_id=evidence.document_id,
            anchor_key="{0}-{1}-{2}".format(evidence.document_id, field_slug, index),
            block_id=evidence.block_id,
            quote_text=evidence.quote_text,
            page_number=evidence.page_number or block.page_number,
            locator={
                "field_name": evidence.field_name,
                "source_label": block.source_label,
                "document_kind": block.document_kind,
            },
        )

    def _build_qualification(self, qualification: LLMExtractionQualification) -> Dict[str, object]:
        """Drop empty values so downstream decision logic sees the same compact qualification shape."""

        qualification_payload = qualification.model_dump(exclude_none=True)
        return {
            key: value
            for key, value in qualification_payload.items()
            if value not in ([], "", None)
        }
