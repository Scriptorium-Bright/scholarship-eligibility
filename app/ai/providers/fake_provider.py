from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.schemas import LLMExtractionResponse


class FakeStructuredOutputProvider:
    """네트워크 호출 없이 향후 LLM 추출 흐름을 검증하기 위한 결정론적 공급자입니다."""

    def __init__(self, response_payload: Optional[Dict[str, Any]] = None):
        """
        테스트에서 재사용할 고정 structured output을 미리 검증해 보관합니다.
        필요하면 호출자가 payload를 주입해 다양한 extraction 케이스를 흉내 낼 수 있게 합니다.
        """

        self._response = LLMExtractionResponse.model_validate(response_payload or self._default_payload())
        self.recorded_prompts: List[str] = []

    def extract_rule(self, *, prompt_text: str) -> LLMExtractionResponse:
        """항상 같은 스키마 유효 payload를 반환하고, 검증용으로 프롬프트를 기록합니다."""

        self.recorded_prompts.append(prompt_text)
        return self._response.model_copy(deep=True)

    def close(self) -> None:
        """fake provider는 외부 리소스를 소유하지 않으므로 close는 아무 동작도 하지 않습니다."""

    @staticmethod
    def _default_payload() -> Dict[str, Any]:
        """baseline 테스트에 사용할 최소한의 스키마 유효 응답을 제공합니다."""

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
