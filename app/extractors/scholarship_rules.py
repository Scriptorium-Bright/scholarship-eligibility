from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from app.models import RuleStatus


@dataclass(frozen=True)
class ExtractedProvenanceAnchor:
    """Provenance anchor candidate produced during heuristic extraction."""

    document_id: int
    anchor_key: str
    block_id: str
    quote_text: str
    page_number: Optional[int] = None
    locator: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractedScholarshipRule:
    """Structured scholarship rule produced before repository persistence."""

    scholarship_name: str
    qualification: Dict[str, object]
    provenance_anchors: List[ExtractedProvenanceAnchor]
    source_document_id: Optional[int]
    application_started_at: Optional[datetime]
    application_ended_at: Optional[datetime]
    summary_text: Optional[str]
    status: RuleStatus = RuleStatus.PUBLISHED


class HeuristicScholarshipRuleExtractor:
    """Extract one scholarship rule from canonical documents using regex heuristics."""

    _GPA_PATTERN = re.compile(r"(?:평점|평균평점|성적).{0,12}?([0-4]\.\d{1,2})\s*이상")
    _INCOME_PATTERN = re.compile(r"소득(?:분위|구간)\s*(\d+)\s*(?:분위|구간)\s*이하")
    _GRADE_PATTERN = re.compile(r"([1-6])학년")

    def extract_notice_rule(
        self,
        notice_title: str,
        canonical_documents: Iterable[object],
        application_started_at: Optional[datetime] = None,
        application_ended_at: Optional[datetime] = None,
        fallback_summary: Optional[str] = None,
    ) -> ExtractedScholarshipRule:
        """Extract a single scholarship rule from all canonical documents for one notice."""

        scholarship_name = self._extract_scholarship_name(notice_title)
        document_blocks = self._flatten_blocks(canonical_documents)
        qualification: Dict[str, object] = {}
        provenance_anchors: List[ExtractedProvenanceAnchor] = []
        source_document_id: Optional[int] = None
        summary_text = fallback_summary

        gpa_match = self._find_first(document_blocks, self._GPA_PATTERN)
        if gpa_match is not None:
            qualification["gpa_min"] = float(gpa_match["match"].group(1))
            provenance_anchors.append(
                self._build_anchor(gpa_match, "gpa-min", "minimum GPA threshold")
            )
            source_document_id = source_document_id or gpa_match["document_id"]
            summary_text = summary_text or gpa_match["text"]

        income_match = self._find_first(document_blocks, self._INCOME_PATTERN)
        if income_match is not None:
            qualification["income_bracket_max"] = int(income_match["match"].group(1))
            provenance_anchors.append(
                self._build_anchor(income_match, "income-bracket-max", "maximum income bracket")
            )
            source_document_id = source_document_id or income_match["document_id"]
            summary_text = summary_text or income_match["text"]

        grade_matches = self._find_all(document_blocks, self._GRADE_PATTERN)
        if grade_matches:
            qualification["grade_levels"] = sorted(
                {int(match["match"].group(1)) for match in grade_matches}
            )
            provenance_anchors.append(
                self._build_anchor(grade_matches[0], "grade-levels", "eligible grade levels")
            )
            source_document_id = source_document_id or grade_matches[0]["document_id"]
            summary_text = summary_text or grade_matches[0]["text"]

        enrollment_match = self._find_first_text(
            document_blocks,
            ("재학생", "복학생", "신입생", "편입생"),
        )
        if enrollment_match is not None:
            statuses = [
                keyword
                for keyword in ("재학생", "복학생", "신입생", "편입생")
                if keyword in enrollment_match["text"]
            ]
            qualification["enrollment_status"] = statuses
            provenance_anchors.append(
                self._build_anchor(enrollment_match, "enrollment-status", "eligible enrollment status")
            )
            source_document_id = source_document_id or enrollment_match["document_id"]
            summary_text = summary_text or enrollment_match["text"]

        required_documents = self._find_required_documents(document_blocks)
        if required_documents:
            qualification["required_documents"] = required_documents["items"]
            provenance_anchors.append(
                self._build_anchor(required_documents["match"], "required-documents", "required documents")
            )
            source_document_id = source_document_id or required_documents["match"]["document_id"]
            summary_text = summary_text or required_documents["match"]["text"]

        if not qualification:
            raise ValueError("No scholarship qualification fields could be extracted")

        return ExtractedScholarshipRule(
            scholarship_name=scholarship_name,
            qualification=qualification,
            provenance_anchors=provenance_anchors,
            source_document_id=source_document_id,
            application_started_at=application_started_at,
            application_ended_at=application_ended_at,
            summary_text=summary_text or fallback_summary or notice_title,
        )

    def _extract_scholarship_name(self, notice_title: str) -> str:
        """Derive a stable scholarship name from the notice title."""

        bracket_match = re.search(r"\[([^\[\]]*장학[^\[\]]*)\]", notice_title)
        if bracket_match is not None:
            return bracket_match.group(1).strip()

        scholarship_match = re.search(r"([가-힣A-Za-z0-9]+장학금)", notice_title)
        if scholarship_match is not None:
            return scholarship_match.group(1).strip()

        student_match = re.search(r"([가-힣A-Za-z0-9]+장학생)", notice_title)
        if student_match is not None:
            return student_match.group(1).strip()

        cleaned_title = re.sub(r"\[[^\]]+\]", "", notice_title)
        cleaned_title = re.sub(r"\s+", " ", cleaned_title).strip()
        return cleaned_title

    def _flatten_blocks(self, canonical_documents: Iterable[object]) -> List[Dict[str, object]]:
        """Flatten canonical document blocks so regex heuristics can scan them uniformly."""

        flattened = []
        for document in canonical_documents:
            for block in document.blocks_json:
                flattened.append(
                    {
                        "document_id": document.id,
                        "block_id": block["block_id"],
                        "text": block["text"],
                        "page_number": block.get("page_number"),
                    }
                )
        return flattened

    def _find_first(self, blocks: Iterable[Dict[str, object]], pattern: re.Pattern):
        """Return the first block that matches the supplied regex pattern."""

        for block in blocks:
            match = pattern.search(block["text"])
            if match is not None:
                return {**block, "match": match}
        return None

    def _find_all(self, blocks: Iterable[Dict[str, object]], pattern: re.Pattern) -> List[Dict[str, object]]:
        """Return all blocks that match the supplied regex pattern."""

        matches = []
        for block in blocks:
            match = pattern.search(block["text"])
            if match is not None:
                matches.append({**block, "match": match})
        return matches

    def _find_first_text(self, blocks: Iterable[Dict[str, object]], keywords: Iterable[str]):
        """Return the first block that contains any of the supplied keywords."""

        for block in blocks:
            if any(keyword in block["text"] for keyword in keywords):
                return block
        return None

    def _find_required_documents(self, blocks: Iterable[Dict[str, object]]):
        """Extract required document lines from canonical blocks."""

        collected_items = []
        matched_block = None
        for block in blocks:
            if any(keyword in block["text"] for keyword in ("지원서", "추천서", "성적증명서", "통장사본")):
                matched_block = matched_block or block
                found_items = re.findall(
                    r"([가-힣A-Za-z0-9()]+(?:지원서|추천서|성적증명서|통장사본))",
                    block["text"],
                )
                for item in found_items:
                    if item not in collected_items:
                        collected_items.append(item)
        if matched_block is None or not collected_items:
            return None
        return {"items": collected_items, "match": matched_block}

    def _build_anchor(
        self,
        block_match: Dict[str, object],
        key_suffix: str,
        description: str,
    ) -> ExtractedProvenanceAnchor:
        """Build a provenance anchor from a matched canonical block."""

        return ExtractedProvenanceAnchor(
            document_id=block_match["document_id"],
            anchor_key="{0}-{1}".format(block_match["document_id"], key_suffix),
            block_id=block_match["block_id"],
            quote_text=block_match["text"],
            page_number=block_match.get("page_number"),
            locator={"description": description},
        )
