from datetime import datetime

import pytest

import app.services.rule_extraction as rule_extraction_module
from app.ai.providers import FakeStructuredOutputProvider
from app.db import create_all_tables, session_scope
from app.extractors import LLMScholarshipRuleExtractor
from app.models import DocumentKind
from app.repositories import CanonicalDocumentRepository, ScholarshipNoticeRepository, ScholarshipRuleRepository
from app.schemas import (
    CanonicalBlock,
    CanonicalDocumentUpsert,
    NoticeAttachmentUpsert,
    ScholarshipNoticeUpsert,
)
from app.services import ScholarshipRuleExtractionService


def _seed_notice_with_canonical_documents():
    with session_scope() as session:
        notice_repository = ScholarshipNoticeRepository(session)
        document_repository = CanonicalDocumentRepository(session)

        notice = notice_repository.upsert_notice(
            ScholarshipNoticeUpsert(
                source_board="jbnu-test",
                source_notice_id="notice-8-4",
                title="[송은장학금] 2026학년도 1학기 장학생 선발 안내",
                notice_url="https://example.test/notices/8-4",
                published_at=datetime(2026, 4, 2, 9, 0, 0),
                application_started_at=datetime(2026, 4, 2, 9, 0, 0),
                application_ended_at=datetime(2026, 4, 9, 18, 0, 0),
                summary="평점과 소득분위를 함께 보는 장학금",
            )
        )
        attachment = notice_repository.add_or_update_attachment(
            notice.id,
            NoticeAttachmentUpsert(
                source_url="https://example.test/notices/8-4/guide.txt",
                file_name="guide.txt",
                media_type="text/plain",
            ),
        )

        notice_document = document_repository.upsert_document(
            CanonicalDocumentUpsert(
                notice_id=notice.id,
                document_kind=DocumentKind.NOTICE_HTML,
                source_label="notice-html",
                canonical_text="\n".join(
                    [
                        "송은장학금",
                        "직전학기 평점평균 3.20 이상인 재학생",
                        "소득분위 8분위 이하 학생",
                        "2학년 또는 3학년 재학생",
                    ]
                ),
                blocks=[
                    CanonicalBlock(
                        block_id="notice-block-1",
                        text="송은장학금",
                        page_number=1,
                    ),
                    CanonicalBlock(
                        block_id="notice-block-2",
                        text="직전학기 평점평균 3.20 이상인 재학생",
                        page_number=1,
                    ),
                    CanonicalBlock(
                        block_id="notice-block-3",
                        text="소득분위 8분위 이하 학생",
                        page_number=1,
                    ),
                    CanonicalBlock(
                        block_id="notice-block-4",
                        text="2학년 또는 3학년 재학생",
                        page_number=1,
                    ),
                ],
            )
        )

        attachment_document = document_repository.upsert_document(
            CanonicalDocumentUpsert(
                notice_id=notice.id,
                attachment_id=attachment.id,
                document_kind=DocumentKind.ATTACHMENT_TEXT,
                source_label="attachment-text",
                canonical_text="제출서류: 장학금지원서, 성적증명서",
                blocks=[
                    CanonicalBlock(
                        block_id="attachment-block-1",
                        text="제출서류: 장학금지원서, 성적증명서",
                        page_number=2,
                    )
                ],
            )
        )

        return notice.id, notice_document.id, attachment_document.id


def _build_fake_payload(*, notice_document_id: int, attachment_document_id: int, required_block_id: str):
    return {
        "scholarship_name": "송은장학금",
        "summary_text": "평점과 소득분위를 함께 보는 장학금",
        "qualification": {
            "gpa_min": 3.2,
            "income_bracket_max": 8,
            "grade_levels": [2, 3],
            "enrollment_status": ["재학생"],
            "required_documents": ["장학금지원서", "성적증명서"],
        },
        "evidence": [
            {
                "field_name": "scholarship_name",
                "document_id": notice_document_id,
                "block_id": "notice-block-1",
                "page_number": 1,
                "quote_text": "송은장학금",
            },
            {
                "field_name": "qualification.gpa_min",
                "document_id": notice_document_id,
                "block_id": "notice-block-2",
                "page_number": 1,
                "quote_text": "직전학기 평점평균 3.20 이상인 재학생",
            },
            {
                "field_name": "qualification.income_bracket_max",
                "document_id": notice_document_id,
                "block_id": "notice-block-3",
                "page_number": 1,
                "quote_text": "소득분위 8분위 이하 학생",
            },
            {
                "field_name": "qualification.grade_levels",
                "document_id": notice_document_id,
                "block_id": "notice-block-4",
                "page_number": 1,
                "quote_text": "2학년 또는 3학년 재학생",
            },
            {
                "field_name": "qualification.enrollment_status",
                "document_id": notice_document_id,
                "block_id": "notice-block-2",
                "page_number": 1,
                "quote_text": "직전학기 평점평균 3.20 이상인 재학생",
            },
            {
                "field_name": "qualification.required_documents",
                "document_id": attachment_document_id,
                "block_id": required_block_id,
                "page_number": 2,
                "quote_text": "제출서류: 장학금지원서, 성적증명서",
            },
        ],
    }


def test_phase8_llm_extractor_service_persists_rule_and_provenance(monkeypatch, tmp_path):
    database_path = tmp_path / "phase8_llm.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    monkeypatch.setenv("JBNU_EXTRACTOR_MODE", "llm")
    monkeypatch.setenv("JBNU_LLM_PROVIDER", "fake")
    monkeypatch.setenv("JBNU_LLM_MAX_CONTEXT_CHARACTERS", "2000")
    create_all_tables()

    notice_id, notice_document_id, attachment_document_id = _seed_notice_with_canonical_documents()
    fake_payload = _build_fake_payload(
        notice_document_id=notice_document_id,
        attachment_document_id=attachment_document_id,
        required_block_id="attachment-block-1",
    )

    monkeypatch.setattr(
        rule_extraction_module,
        "build_structured_output_provider",
        lambda settings: FakeStructuredOutputProvider(fake_payload),
    )

    service = ScholarshipRuleExtractionService()
    assert isinstance(service._extractor, LLMScholarshipRuleExtractor)

    saved_rules = service.extract_notice(notice_id)
    assert len(saved_rules) == 1

    with session_scope() as session:
        rule_repository = ScholarshipRuleRepository(session)
        document_repository = CanonicalDocumentRepository(session)
        notice_rules = rule_repository.list_rules_for_notice(notice_id)
        notice_anchors = document_repository.list_anchors(notice_document_id)
        attachment_anchors = document_repository.list_anchors(attachment_document_id)

        assert notice_rules[0].scholarship_name == "송은장학금"
        assert notice_rules[0].document_id == notice_document_id
        assert notice_rules[0].qualification_json["gpa_min"] == 3.2
        assert notice_rules[0].qualification_json["income_bracket_max"] == 8
        assert notice_rules[0].qualification_json["grade_levels"] == [2, 3]
        assert notice_rules[0].qualification_json["enrollment_status"] == ["재학생"]
        assert notice_rules[0].qualification_json["required_documents"] == ["장학금지원서", "성적증명서"]
        assert len(notice_rules[0].provenance_keys_json) == 6
        assert any(anchor.block_id == "notice-block-2" for anchor in notice_anchors)
        assert any(anchor.block_id == "attachment-block-1" for anchor in attachment_anchors)


def test_phase8_llm_extractor_rejects_unknown_evidence_block(monkeypatch, tmp_path):
    database_path = tmp_path / "phase8_llm_invalid.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    monkeypatch.setenv("JBNU_EXTRACTOR_MODE", "llm")
    monkeypatch.setenv("JBNU_LLM_PROVIDER", "fake")
    create_all_tables()

    notice_id, notice_document_id, attachment_document_id = _seed_notice_with_canonical_documents()
    fake_payload = _build_fake_payload(
        notice_document_id=notice_document_id,
        attachment_document_id=attachment_document_id,
        required_block_id="missing-block-id",
    )

    monkeypatch.setattr(
        rule_extraction_module,
        "build_structured_output_provider",
        lambda settings: FakeStructuredOutputProvider(fake_payload),
    )

    with pytest.raises(ValueError, match="unknown canonical block"):
        ScholarshipRuleExtractionService().extract_notice(notice_id)
