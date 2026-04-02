from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.schemas import LLMExtractionResponse


class FakeStructuredOutputProvider:
    """Deterministic provider used to test future LLM orchestration without network calls."""

    def __init__(self, response_payload: Optional[Dict[str, Any]] = None):
        self._response = LLMExtractionResponse.model_validate(response_payload or self._default_payload())
        self.recorded_prompts: List[str] = []

    def extract_rule(self, *, prompt_text: str) -> LLMExtractionResponse:
        """Return a stable schema-valid payload and keep the latest prompt for assertions."""

        self.recorded_prompts.append(prompt_text)
        return self._response.model_copy(deep=True)

    def close(self) -> None:
        """Fake provider does not own external resources, so close is a no-op."""

    @staticmethod
    def _default_payload() -> Dict[str, Any]:
        """Provide one minimal but schema-valid extraction response for baseline tests."""

        return {
            "scholarship_name": "테스트 장학금",
            "summary_text": "fake provider baseline response",
            "qualification": {
                "gpa_min": 3.0,
                "income_bracket_max": 8,
                "grade_levels": [1, 2, 3, 4],
                "enrollment_status": ["재학생"],
                "required_documents": ["장학금지원서"],
            },
            "evidence": [
                {
                    "field_name": "scholarship_name",
                    "document_id": 1,
                    "block_id": "fake-block-1",
                    "page_number": 1,
                    "quote_text": "테스트 장학금",
                }
            ],
        }
