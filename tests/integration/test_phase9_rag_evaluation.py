from pathlib import Path

from scripts.evaluate_phase9_rag import (
    evaluate_rag_answers,
    format_rag_summary_markdown,
    load_question_set,
)


def test_phase9_rag_evaluation_loads_question_set_and_formats_markdown():
    fixtures_dir = Path("tests/fixtures/phase9_rag_questions")

    question_set = load_question_set(fixtures_dir)
    evaluation_run = evaluate_rag_answers(fixtures_dir)
    markdown = format_rag_summary_markdown(evaluation_run.summary)

    assert len(question_set) == 4
    assert question_set[0].sample_id == "alpha-gpa-grounded"
    assert question_set[1].sample_id == "beta-documents-grounded"
    assert "| Sample Count | Groundedness | Citation Coverage |" in markdown
    assert "| 4 | 100.00% | 100.00% | 100.00% |" in markdown


def test_phase9_rag_evaluation_reports_groundedness_and_refusal_metrics():
    fixtures_dir = Path("tests/fixtures/phase9_rag_questions")

    evaluation_run = evaluate_rag_answers(fixtures_dir)
    summary = evaluation_run.summary
    result_by_id = {
        result.sample_id: result
        for result in evaluation_run.results
    }

    assert summary.sample_count == 4
    assert summary.grounded_sample_count == 2
    assert summary.groundedness_rate == 1.0
    assert summary.citation_coverage_rate == 1.0
    assert summary.refusal_precision == 1.0
    assert summary.average_latency_ms > 0
    assert summary.p95_latency_ms > 0

    assert result_by_id["alpha-gpa-grounded"].actual_answer_mode == "grounded"
    assert result_by_id["alpha-gpa-grounded"].grounded is True
    assert result_by_id["beta-documents-grounded"].citation_coverage_count == 1
    assert result_by_id["gamma-no-evidence-refusal"].actual_answer_mode == "no_evidence"
    assert result_by_id["gamma-no-evidence-refusal"].refusal_correct is True
    assert result_by_id["delta-guardrail-refusal"].actual_answer_mode == "guardrail"
    assert result_by_id["delta-guardrail-refusal"].refusal_correct is True
