from fastapi.testclient import TestClient

from app.ai.providers import FakeEmbeddingProvider, FakeGroundedAnswerProvider
from app.main import create_app
from app.services import ScholarshipRagAnswerService, ScholarshipRagRetrievalService
from tests.support.rag_answer_seed import seed_phase9_rag_answer_data


def test_phase9_rag_api_returns_grounded_answer_with_citations(monkeypatch, tmp_path):
    seed_phase9_rag_answer_data(monkeypatch, tmp_path)
    service = ScholarshipRagAnswerService(
        answer_provider=FakeGroundedAnswerProvider(
            response_payload={
                "answer_text": "통합장학금은 직전학기 평점평균 3.80 이상인 재학생을 대상으로 합니다."
            }
        ),
        retrieval_service=ScholarshipRagRetrievalService(
            embedding_provider=FakeEmbeddingProvider(
                dimensions=3,
                predefined_vectors={"통합장학금 성적 기준이 뭐야?": [1.0, 0.0, 0.0]},
            )
        ),
    )
    monkeypatch.setattr("app.api.routers.scholarships.ScholarshipRagAnswerService", lambda: service)
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/scholarships/ask",
        json={"question": "통합장학금 성적 기준이 뭐야?", "limit": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer_mode"] == "grounded"
    assert body["citations"][0]["block_id"] == "notice-block-1"
    assert body["citations"][0]["quote_text"] == "직전학기 평점평균 3.80 이상인 재학생"
    assert body["has_evidence"] is True


def test_phase9_rag_api_returns_guardrail_for_profile_decision_question(monkeypatch, tmp_path):
    seed_phase9_rag_answer_data(monkeypatch, tmp_path)
    service = ScholarshipRagAnswerService(
        answer_provider=FakeGroundedAnswerProvider(),
        retrieval_service=ScholarshipRagRetrievalService(
            embedding_provider=FakeEmbeddingProvider(
                dimensions=3,
                predefined_vectors={"제 학점 3.8과 소득분위 6이면 지원 가능해?": [1.0, 0.0, 0.0]},
            )
        ),
    )
    monkeypatch.setattr("app.api.routers.scholarships.ScholarshipRagAnswerService", lambda: service)
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/scholarships/ask",
        json={"question": "제 학점 3.8과 소득분위 6이면 지원 가능해?", "limit": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer_mode"] == "guardrail"
    assert body["recommended_endpoint"] == "/api/v1/scholarships/eligibility"
    assert body["citations"] == []
