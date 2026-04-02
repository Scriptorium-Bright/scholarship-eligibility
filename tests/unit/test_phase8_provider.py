import json

import httpx
import pytest

from app.ai.providers import (
    FakeStructuredOutputProvider,
    OpenAICompatibleStructuredOutputProvider,
    StructuredOutputProviderResponseError,
    build_structured_output_provider,
)
from app.core.config import get_settings


def test_phase8_fake_provider_returns_schema_valid_response():
    provider = FakeStructuredOutputProvider()

    response = provider.extract_rule(prompt_text="장학 규정을 구조화해줘")

    assert response.scholarship_name == "테스트 장학금"
    assert response.evidence[0].block_id == "fake-block-1"
    assert provider.recorded_prompts == ["장학 규정을 구조화해줘"]


def test_phase8_openai_provider_posts_chat_completion_and_parses_response():
    captured = {}
    payload = {
        "scholarship_name": "송은장학금",
        "summary_text": "평점과 소득분위를 보는 장학금",
        "qualification": {
            "gpa_min": 3.2,
            "income_bracket_max": 8,
            "grade_levels": [1, 2, 3],
            "enrollment_status": ["재학생"],
            "required_documents": ["장학금지원서"],
        },
        "evidence": [
            {
                "field_name": "qualification.gpa_min",
                "document_id": 101,
                "block_id": "block-1",
                "page_number": 1,
                "quote_text": "직전학기 평점평균 3.20 이상",
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        captured["json"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(payload, ensure_ascii=False),
                        }
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://llm.example.test/v1",
    )
    provider = OpenAICompatibleStructuredOutputProvider(
        base_url="https://llm.example.test/v1",
        api_key="secret-key",
        model="test-model",
        client=client,
    )

    response = provider.extract_rule(prompt_text="장학 규정을 JSON으로 반환해줘")

    assert response.scholarship_name == "송은장학금"
    assert captured["path"] == "/v1/chat/completions"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["messages"][1]["content"] == "장학 규정을 JSON으로 반환해줘"
    assert captured["headers"]["authorization"] == "Bearer secret-key"

    provider.close()
    client.close()


def test_phase8_openai_provider_rejects_invalid_structured_output():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "{\"scholarship_name\": \"송은장학금\"}",
                        }
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://llm.example.test/v1",
    )
    provider = OpenAICompatibleStructuredOutputProvider(
        base_url="https://llm.example.test/v1",
        model="test-model",
        client=client,
    )

    with pytest.raises(StructuredOutputProviderResponseError):
        provider.extract_rule(prompt_text="장학 규정을 JSON으로 반환해줘")

    provider.close()
    client.close()


def test_phase8_provider_factory_reads_settings(monkeypatch):
    monkeypatch.setenv("JBNU_EXTRACTOR_MODE", "llm")
    monkeypatch.setenv("JBNU_LLM_PROVIDER", "fake")
    monkeypatch.setenv("JBNU_LLM_MODEL", "test-model")
    monkeypatch.setenv("JBNU_LLM_TIMEOUT_SECONDS", "42")
    monkeypatch.setenv("JBNU_LLM_MAX_CONTEXT_CHARACTERS", "7000")

    settings = get_settings()
    provider = build_structured_output_provider(settings)

    assert settings.extractor_mode == "llm"
    assert settings.llm_model == "test-model"
    assert settings.llm_timeout_seconds == 42
    assert settings.llm_max_context_characters == 7000
    assert isinstance(provider, FakeStructuredOutputProvider)
