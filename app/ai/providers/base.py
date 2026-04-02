from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas import LLMExtractionResponse


class StructuredOutputProviderError(RuntimeError):
    """Base exception raised when a structured output provider cannot complete extraction."""


class StructuredOutputProviderTransportError(StructuredOutputProviderError):
    """Raised when the upstream provider cannot be reached or returns an HTTP error."""


class StructuredOutputProviderResponseError(StructuredOutputProviderError):
    """Raised when the upstream provider responds with an invalid schema payload."""


@runtime_checkable
class StructuredOutputProvider(Protocol):
    """Common provider contract used by future LLM extractors."""

    def extract_rule(self, *, prompt_text: str) -> LLMExtractionResponse:
        """Call one model provider and return one schema-validated extraction payload."""

    def close(self) -> None:
        """Release any provider resources such as shared HTTP clients."""
