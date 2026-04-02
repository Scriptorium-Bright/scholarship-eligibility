from datetime import datetime
import logging

import pytest

import app.services.rule_extraction as rule_extraction_module
from app.ai.providers import FakeStructuredOutputProvider, StructuredOutputProviderTransportError
from app.db import create_all_tables, session_scope
from app.models import DocumentKind
from app.repositories import CanonicalDocumentRepository, ScholarshipNoticeRepository, ScholarshipRuleRepository
from app.schemas import (
    CanonicalBlock,
    CanonicalDocumentUpsert,
    NoticeAttachmentUpsert,
    ScholarshipNoticeUpsert,
)
from app.services import ScholarshipRuleExtractionService


class FailingStructuredOutputProvider:
    """hybrid fallback 경로를 검증하기 위해 항상 transport error를 내는 테스트용 공급자입니다."""

    def extract_rule(self, *, prompt_text: str):
        """실제 네트워크 장애를 흉내 내기 위해 transport error를 즉시 발생시킵니다."""

        raise StructuredOutputProviderTransportError("synthetic transport failure")

    def close(self) -> None:
        """테스트 공급자는 외부 리소스를 사용하지 않으므로 정리 동작이 없습니다."""


def _seed_notice_with_canonical_documents():
    with session_scope() as session:
        notice_repository = ScholarshipNoticeRepository(session)
        document_repository = CanonicalDocumentRepository(session)

        notice = notice_repository.upsert_notice(
            ScholarshipNoticeUpsert(
                source_board="jbnu-test",
                source_notice_id="notice-8-5",
                title="[송은장학금] 2026학년도 1학기 장학생 선발 안내",
                notice_url="https://example.test/notices/8-5",
                published_at=datetime(2026, 4, 2, 9, 0, 0),
                application_started_at=datetime(2026, 4, 2, 9, 0, 0),
                application_ended_at=datetime(2026, 4, 9, 18, 0, 0),
                summary="평점과 소득분위를 함께 보는 장학금",
            )
        )
        attachment = notice_repository.add_or_update_attachment(
            notice.id,
            NoticeAttachmentUpsert(
                source_url="https://example.test/notices/8-5/guide.txt",
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
                    CanonicalBlock(block_id="notice-block-1", text="송은장학금", page_number=1),
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


def _build_invalid_block_payload(*, notice_document_id: int, attachment_document_id: int):
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
                "field_name": "qualification.gpa_min",
                "document_id": notice_document_id,
                "block_id": "notice-block-2",
                "page_number": 1,
                "quote_text": "직전학기 평점평균 3.20 이상인 재학생",
            },
            {
                "field_name": "qualification.required_documents",
                "document_id": attachment_document_id,
                "block_id": "missing-block-id",
                "page_number": 2,
                "quote_text": "제출서류: 장학금지원서, 성적증명서",
            },
        ],
    }


def test_phase8_hybrid_mode_falls_back_when_llm_evidence_is_invalid(monkeypatch, tmp_path, caplog):
    database_path = tmp_path / "phase8_hybrid_invalid.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    monkeypatch.setenv("JBNU_EXTRACTOR_MODE", "hybrid")
    monkeypatch.setenv("JBNU_LLM_PROVIDER", "fake")
    create_all_tables()

    notice_id, notice_document_id, attachment_document_id = _seed_notice_with_canonical_documents()
    fake_payload = _build_invalid_block_payload(
        notice_document_id=notice_document_id,
        attachment_document_id=attachment_document_id,
    )

    caplog.set_level(logging.WARNING, logger="app.services.extraction_logging")
    monkeypatch.setattr(
        rule_extraction_module,
        "build_structured_output_provider",
        lambda settings: FakeStructuredOutputProvider(fake_payload),
    )

    saved_rules = ScholarshipRuleExtractionService().extract_notice(notice_id)

    assert len(saved_rules) == 1
    with session_scope() as session:
        rule_repository = ScholarshipRuleRepository(session)
        notice_rules = rule_repository.list_rules_for_notice(notice_id)
        assert notice_rules[0].qualification_json["gpa_min"] == 3.2
        assert "장학금지원서" in notice_rules[0].qualification_json["required_documents"]

    assert "requested_mode=hybrid" in caplog.text
    assert "extractor_used=heuristic" in caplog.text
    assert "fallback_used=True" in caplog.text
    assert "error_type=ValueError" in caplog.text


def test_phase8_hybrid_mode_falls_back_when_provider_raises_transport_error(
    monkeypatch, tmp_path, caplog
):
    database_path = tmp_path / "phase8_hybrid_transport.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    monkeypatch.setenv("JBNU_EXTRACTOR_MODE", "hybrid")
    monkeypatch.setenv("JBNU_LLM_PROVIDER", "openai_compatible")
    create_all_tables()

    notice_id, _, _ = _seed_notice_with_canonical_documents()

    caplog.set_level(logging.WARNING, logger="app.services.extraction_logging")
    monkeypatch.setattr(
        rule_extraction_module,
        "build_structured_output_provider",
        lambda settings: FailingStructuredOutputProvider(),
    )

    saved_rules = ScholarshipRuleExtractionService().extract_notice(notice_id)

    assert len(saved_rules) == 1
    assert "extractor_used=heuristic" in caplog.text
    assert "fallback_used=True" in caplog.text
    assert "error_type=StructuredOutputProviderTransportError" in caplog.text


def test_phase8_llm_mode_still_raises_when_fallback_is_disabled(monkeypatch, tmp_path, caplog):
    database_path = tmp_path / "phase8_llm_no_fallback.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    monkeypatch.setenv("JBNU_EXTRACTOR_MODE", "llm")
    monkeypatch.setenv("JBNU_LLM_PROVIDER", "openai_compatible")
    create_all_tables()

    notice_id, _, _ = _seed_notice_with_canonical_documents()

    caplog.set_level(logging.ERROR, logger="app.services.extraction_logging")
    monkeypatch.setattr(
        rule_extraction_module,
        "build_structured_output_provider",
        lambda settings: FailingStructuredOutputProvider(),
    )

    with pytest.raises(StructuredOutputProviderTransportError, match="synthetic transport failure"):
        ScholarshipRuleExtractionService().extract_notice(notice_id)

    assert "requested_mode=llm" in caplog.text
    assert "extractor_used=llm" in caplog.text
    assert "success=False" in caplog.text
    assert "fallback_used=False" in caplog.text
