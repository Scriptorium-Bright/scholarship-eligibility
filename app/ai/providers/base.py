from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas import LLMExtractionResponse


class StructuredOutputProviderError(RuntimeError):
    """구조화 출력 공급자가 추출을 완료하지 못했을 때 쓰는 공통 예외입니다."""


class StructuredOutputProviderTransportError(StructuredOutputProviderError):
    """상위 공급자에 연결할 수 없거나 HTTP 오류가 반환될 때 발생합니다."""


class StructuredOutputProviderResponseError(StructuredOutputProviderError):
    """상위 공급자가 스키마에 맞지 않는 응답을 보냈을 때 발생합니다."""


@runtime_checkable
class StructuredOutputProvider(Protocol):
    """향후 LLM 추출기들이 공통으로 따를 공급자 계약입니다."""

    def extract_rule(self, *, prompt_text: str) -> LLMExtractionResponse:
        """프롬프트를 받아 스키마 검증이 끝난 추출 결과를 반환합니다."""

    def close(self) -> None:
        """공유 HTTP 클라이언트 같은 공급자 리소스를 정리합니다."""
