"""향후 LLM 추출 단계에서 사용할 구조화 출력 공급자 구현 모음입니다."""

from __future__ import annotations

from typing import Optional

from app.ai.providers.base import (
    StructuredOutputProvider,
    StructuredOutputProviderError,
    StructuredOutputProviderResponseError,
    StructuredOutputProviderTransportError,
)
from app.ai.providers.fake_provider import FakeStructuredOutputProvider
from app.ai.providers.openai_provider import OpenAICompatibleStructuredOutputProvider
from app.core.config import Settings, get_settings


def build_structured_output_provider(settings: Optional[Settings] = None) -> StructuredOutputProvider:
    """애플리케이션 설정값을 기준으로 사용할 공급자 구현체를 생성합니다."""

    active_settings = settings or get_settings()
    if active_settings.llm_provider == "fake":
        return FakeStructuredOutputProvider()
    if active_settings.llm_provider == "openai_compatible":
        return OpenAICompatibleStructuredOutputProvider(
            base_url=active_settings.llm_api_base_url,
            api_key=active_settings.llm_api_key,
            model=active_settings.llm_model,
            timeout_seconds=active_settings.llm_timeout_seconds,
        )
    raise ValueError("Unsupported LLM provider: {0}".format(active_settings.llm_provider))


__all__ = [
    "FakeStructuredOutputProvider",
    "OpenAICompatibleStructuredOutputProvider",
    "StructuredOutputProvider",
    "StructuredOutputProviderError",
    "StructuredOutputProviderResponseError",
    "StructuredOutputProviderTransportError",
    "build_structured_output_provider",
]
