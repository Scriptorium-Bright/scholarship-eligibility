from pathlib import Path

from scripts.evaluate_phase8_extraction import (
    evaluate_all_modes,
    format_summary_markdown,
    load_gold_set,
)


def test_phase8_evaluation_loads_gold_set_and_formats_markdown():
    fixtures_dir = Path("tests/fixtures/phase8_gold_set")

    gold_set = load_gold_set(fixtures_dir)
    summaries = evaluate_all_modes(fixtures_dir)
    markdown = format_summary_markdown(summaries)

    assert len(gold_set) == 4
    assert gold_set[0].sample_id == "alpha-standard-success"
    assert "| Mode | Success Rate | Field Exact Match |" in markdown
    assert "| hybrid |" in markdown


def test_phase8_evaluation_shows_hybrid_balance_between_accuracy_and_reliability():
    fixtures_dir = Path("tests/fixtures/phase8_gold_set")

    summaries = evaluate_all_modes(fixtures_dir)
    heuristic = summaries["heuristic"]
    llm = summaries["llm"]
    hybrid = summaries["hybrid"]

    assert heuristic.sample_count == 4
    assert llm.sample_count == 4
    assert hybrid.sample_count == 4

    assert heuristic.extraction_success_rate == 1.0
    assert llm.extraction_success_rate == 0.5
    assert hybrid.extraction_success_rate == 1.0

    assert heuristic.field_exact_match_rate == 13 / 24
    assert llm.field_exact_match_rate == 12 / 24
    assert hybrid.field_exact_match_rate == 19 / 24

    assert heuristic.evidence_coverage_rate == 12 / 21
    assert llm.evidence_coverage_rate == 11 / 21
    assert hybrid.evidence_coverage_rate == 17 / 21

    assert hybrid.fallback_recovery_rate == 1.0
    assert hybrid.field_exact_match_rate > heuristic.field_exact_match_rate
    assert hybrid.field_exact_match_rate > llm.field_exact_match_rate
