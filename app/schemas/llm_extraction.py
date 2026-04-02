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
    """추출된 필드 하나를 특정 문서의 canonical block 하나와 다시 연결하는 근거 모델입니다."""

    field_name: LLMExtractionFieldName
    document_id: int = Field(ge=1)
    block_id: str = Field(min_length=1)
    page_number: Optional[int] = Field(default=None, ge=1)
    quote_text: str = Field(min_length=1)


class LLMExtractionQualification(StrictSchema):
    """LLM 추출기가 반환해야 하는 구조화 qualification payload입니다."""

    gpa_min: Optional[float] = Field(default=None, ge=0.0, le=4.5)
    income_bracket_max: Optional[int] = Field(default=None, ge=0, le=10)
    grade_levels: List[int] = Field(default_factory=list)
    enrollment_status: List[str] = Field(default_factory=list)
    required_documents: List[str] = Field(default_factory=list)

    @field_validator("grade_levels")
    @classmethod
    def _normalize_grade_levels(cls, value: List[int]) -> List[int]:
        """학년 배열을 중복 없는 안정된 형태로 맞춰 downstream 비교를 단순하게 합니다."""

        return sorted({int(level) for level in value})

    @field_validator("enrollment_status", "required_documents")
    @classmethod
    def _remove_blank_strings(cls, value: List[str]) -> List[str]:
        """빈 문자열을 제거해 evidence 품질 지표가 의미 없는 값에 오염되지 않게 합니다."""

        return [item.strip() for item in value if item and item.strip()]


class LLMExtractionResponse(StrictSchema):
    """향후 LLM 추출 공급자들이 따라야 하는 최상위 structured output 계약입니다."""

    scholarship_name: str = Field(min_length=1)
    summary_text: Optional[str] = None
    qualification: LLMExtractionQualification
    evidence: List[LLMExtractionEvidence] = Field(default_factory=list)
