import json

import httpx

from app.ai.providers import (
    FakeGroundedAnswerProvider,
    OpenAICompatibleGroundedAnswerProvider,
    build_grounded_answer_provider,
)
from app.core.config import get_settings


def test_phase9_fake_grounded_answer_provider_records_question_and_prompt():
    provider = FakeGroundedAnswerProvider(
        response_payload={"answer_text": "평점 3.80 이상 재학생이 대상입니다."}
    )

    response = provider.generate_answer(
        question="통합장학금 성적 기준이 뭐야?",
        prompt_text="[retrieved chunks]\n[block_id=notice-block-1] 직전학기 평점평균 3.80 이상인 재학생",
    )

    assert response.answer_text == "평점 3.80 이상 재학생이 대상입니다."
    assert provider.recorded_questions == ["통합장학금 성적 기준이 뭐야?"]
    assert "notice-block-1" in provider.recorded_prompts[0]


def test_phase9_openai_grounded_answer_provider_posts_chat_completion_and_parses_response():
    captured = {}

    def handler(request):
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        captured["json"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "answer_text": "통합장학금은 직전학기 평점평균 3.80 이상 재학생 대상입니다."
                                }
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://chat.example.test/v1",
    )
    provider = OpenAICompatibleGroundedAnswerProvider(
        base_url="https://chat.example.test/v1",
        api_key="secret-key",
        model="answer-model",
        client=client,
    )

    response = provider.generate_answer(
        question="통합장학금 성적 기준이 뭐야?",
        prompt_text="[retrieved chunks]\n[block_id=notice-block-1] 직전학기 평점평균 3.80 이상인 재학생",
    )

    assert captured["path"] == "/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer secret-key"
    assert captured["json"]["model"] == "answer-model"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert "통합장학금 성적 기준이 뭐야?" in captured["json"]["messages"][1]["content"]
    assert response.answer_text == "통합장학금은 직전학기 평점평균 3.80 이상 재학생 대상입니다."

    provider.close()
    client.close()


def test_phase9_grounded_answer_provider_factory_reads_settings(monkeypatch):
    monkeypatch.setenv("JBNU_LLM_PROVIDER", "fake")
    monkeypatch.setenv("JBNU_LLM_MODEL", "test-answer-model")

    settings = get_settings()
    provider = build_grounded_answer_provider(settings)

    assert settings.llm_provider == "fake"
    assert settings.llm_model == "test-answer-model"
    assert isinstance(provider, FakeGroundedAnswerProvider)
