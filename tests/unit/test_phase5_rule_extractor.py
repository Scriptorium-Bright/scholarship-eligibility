from types import SimpleNamespace

from app.extractors import HeuristicScholarshipRuleExtractor


def test_phase5_rule_extractor_builds_structured_rule_and_provenance():
    extractor = HeuristicScholarshipRuleExtractor()
    canonical_documents = [
        SimpleNamespace(
            id=101,
            blocks_json=[
                {
                    "block_id": "block-1",
                    "text": "직전학기 평점평균 3.20 이상인 재학생",
                    "page_number": 1,
                },
                {
                    "block_id": "block-2",
                    "text": "소득분위 8분위 이하 학생을 우대함",
                    "page_number": 1,
                },
                {
                    "block_id": "block-3",
                    "text": "제출서류: 장학금지원서, 성적증명서, 통장사본",
                    "page_number": 1,
                },
            ],
        )
    ]

    rule = extractor.extract_notice_rule(
        notice_title="[학부] 2026학년도 1학기 발전지원재단 [송은장학금] 장학생 선발 안내",
        canonical_documents=canonical_documents,
    )

    assert rule.scholarship_name == "송은장학금"
    assert rule.qualification["gpa_min"] == 3.2
    assert rule.qualification["income_bracket_max"] == 8
    assert rule.qualification["enrollment_status"] == ["재학생"]
    assert "장학금지원서" in rule.qualification["required_documents"]
    assert rule.source_document_id == 101
    assert len(rule.provenance_anchors) >= 4
