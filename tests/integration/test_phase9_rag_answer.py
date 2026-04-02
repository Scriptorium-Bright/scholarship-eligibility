from app.ai.providers import FakeEmbeddingProvider, FakeGroundedAnswerProvider
from app.services import (
    RagPromptBuilder,
    ScholarshipRagAnswerService,
    ScholarshipRagRetrievalService,
)
from tests.support.rag_answer_seed import seed_phase9_rag_answer_data


def test_phase9_rag_answer_service_returns_grounded_answer_and_citations(
    monkeypatch,
    tmp_path,
):
    seed_phase9_rag_answer_data(monkeypatch, tmp_path)
    retrieval_service = ScholarshipRagRetrievalService(
        embedding_provider=FakeEmbeddingProvider(
            dimensions=3,
            predefined_vectors={"통합장학금 성적 기준이 뭐야?": [1.0, 0.0, 0.0]},
        )
    )
    answer_provider = FakeGroundedAnswerProvider(
        response_payload={
            "answer_text": "통합장학금은 직전학기 평점평균 3.80 이상인 재학생을 대상으로 합니다."
        }
    )
    service = ScholarshipRagAnswerService(
        answer_provider=answer_provider,
        retrieval_service=retrieval_service,
        prompt_builder=RagPromptBuilder(max_characters=6000),
    )

    response = service.answer("통합장학금 성적 기준이 뭐야?", limit=2)

    assert response.answer_mode == "grounded"
    assert response.has_evidence is True
    assert response.retrieval_mode == "hybrid"
    assert response.citations[0].block_id == "notice-block-1"
    assert response.citations[0].quote_text == "직전학기 평점평균 3.80 이상인 재학생"
    assert "3.80" in response.answer_text
    assert answer_provider.recorded_questions == ["통합장학금 성적 기준이 뭐야?"]
    assert "notice-block-1" in answer_provider.recorded_prompts[0]


def test_phase9_rag_answer_service_returns_no_evidence_refusal(monkeypatch, tmp_path):
    seed_phase9_rag_answer_data(monkeypatch, tmp_path)
    retrieval_service = ScholarshipRagRetrievalService(
        embedding_provider=FakeEmbeddingProvider(
            dimensions=3,
            predefined_vectors={"기숙사 입주 가능해?": [0.0, 0.0, 0.0]},
        )
    )
    answer_provider = FakeGroundedAnswerProvider()
    service = ScholarshipRagAnswerService(
        answer_provider=answer_provider,
        retrieval_service=retrieval_service,
    )

    response = service.answer("기숙사 입주 가능해?", limit=2)

    assert response.answer_mode == "no_evidence"
    assert response.has_evidence is False
    assert response.citations == []
    assert "근거를 찾지 못했습니다" in response.answer_text
    assert answer_provider.recorded_prompts == []


def test_phase9_rag_answer_service_redirects_profile_decision_questions(monkeypatch, tmp_path):
    seed_phase9_rag_answer_data(monkeypatch, tmp_path)
    retrieval_service = ScholarshipRagRetrievalService(
        embedding_provider=FakeEmbeddingProvider(
            dimensions=3,
            predefined_vectors={"제 학점 3.8과 소득분위 6이면 지원 가능해?": [1.0, 0.0, 0.0]},
        )
    )
    answer_provider = FakeGroundedAnswerProvider()
    service = ScholarshipRagAnswerService(
        answer_provider=answer_provider,
        retrieval_service=retrieval_service,
    )

    response = service.answer("제 학점 3.8과 소득분위 6이면 지원 가능해?", limit=2)

    assert response.answer_mode == "guardrail"
    assert response.recommended_endpoint == "/api/v1/scholarships/eligibility"
    assert response.retrieval_mode == "guardrail"
    assert response.citations == []
    assert answer_provider.recorded_prompts == []
