from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field, field_validator

from app.schemas.domain import StrictSchema

LLMExtractionFieldName = Literal[
    "scholarship_name",
    "summary_text",
    "qualification.gpa_min",
    "qualification.income_bracket_max",
    "qualification.grade_levels",
    "qualification.enrollment_status",
    "qualification.required_documents",
]


class LLMExtractionEvidence(StrictSchema):
    """Ground one extracted field back to one canonical block in one source document."""

    field_name: LLMExtractionFieldName
    document_id: int = Field(ge=1)
    block_id: str = Field(min_length=1)
    page_number: Optional[int] = Field(default=None, ge=1)
    quote_text: str = Field(min_length=1)


class LLMExtractionQualification(StrictSchema):
    """Structured qualification payload that an LLM extractor must return."""

    gpa_min: Optional[float] = Field(default=None, ge=0.0, le=4.5)
    income_bracket_max: Optional[int] = Field(default=None, ge=0, le=10)
    grade_levels: List[int] = Field(default_factory=list)
    enrollment_status: List[str] = Field(default_factory=list)
    required_documents: List[str] = Field(default_factory=list)

    @field_validator("grade_levels")
    @classmethod
    def _normalize_grade_levels(cls, value: List[int]) -> List[int]:
        """Keep grade levels unique and stable for downstream deterministic comparison."""

        return sorted({int(level) for level in value})

    @field_validator("enrollment_status", "required_documents")
    @classmethod
    def _remove_blank_strings(cls, value: List[str]) -> List[str]:
        """Strip empty strings so evidence quality metrics are not polluted by filler values."""

        return [item.strip() for item in value if item and item.strip()]


class LLMExtractionResponse(StrictSchema):
    """Top-level structured output contract used by future LLM extraction providers."""

    scholarship_name: str = Field(min_length=1)
    summary_text: Optional[str] = None
    qualification: LLMExtractionQualification
    evidence: List[LLMExtractionEvidence] = Field(default_factory=list)

