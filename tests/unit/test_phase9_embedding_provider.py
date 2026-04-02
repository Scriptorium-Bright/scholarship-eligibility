import json

import httpx

from app.ai.providers import (
    FakeEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider,
)
from app.core.config import get_settings


def test_phase9_fake_embedding_provider_returns_deterministic_vectors():
    provider = FakeEmbeddingProvider()

    vectors = provider.embed_documents(texts=["평점 3.5 이상", "평점 3.5 이상"])
    query_vector = provider.embed_query(text="평점 3.5 이상")

    assert vectors[0] == vectors[1]
    assert vectors[0] == query_vector
    assert provider.recorded_document_batches == [["평점 3.5 이상", "평점 3.5 이상"]]
    assert provider.recorded_queries == ["평점 3.5 이상"]


def test_phase9_openai_embedding_provider_posts_embeddings_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        captured["json"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 0, "embedding": [1.0, 0.0, 0.0]},
                    {"index": 1, "embedding": [0.0, 1.0, 0.0]},
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://emb.example.test/v1",
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://emb.example.test/v1",
        api_key="secret-key",
        model="embed-model",
        client=client,
    )

    vectors = provider.embed_documents(texts=["평점 기준", "소득 기준"])

    assert captured["path"] == "/v1/embeddings"
    assert captured["headers"]["authorization"] == "Bearer secret-key"
    assert captured["json"]["model"] == "embed-model"
    assert captured["json"]["input"] == ["평점 기준", "소득 기준"]
    assert vectors == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    provider.close()
    client.close()


def test_phase9_embedding_provider_factory_reads_settings(monkeypatch):
    monkeypatch.setenv("JBNU_EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv("JBNU_EMBEDDING_MODEL", "test-embedding-model")
    monkeypatch.setenv("JBNU_EMBEDDING_TIMEOUT_SECONDS", "42")

    settings = get_settings()
    provider = build_embedding_provider(settings)

    assert settings.embedding_provider == "fake"
    assert settings.embedding_model == "test-embedding-model"
    assert settings.embedding_timeout_seconds == 42
    assert isinstance(provider, FakeEmbeddingProvider)
