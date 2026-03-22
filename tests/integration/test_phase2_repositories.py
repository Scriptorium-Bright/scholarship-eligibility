from datetime import datetime

from app.core.time import ASIA_SEOUL
from app.db import create_all_tables, session_scope
from app.models import DocumentKind
from app.repositories import (
    CanonicalDocumentRepository,
    ScholarshipNoticeRepository,
    ScholarshipRuleRepository,
)
from app.schemas import (
    CanonicalBlock,
    CanonicalDocumentUpsert,
    NoticeAttachmentUpsert,
    ProvenanceAnchorCreate,
    ScholarshipNoticeUpsert,
    ScholarshipRuleCreate,
)


def test_phase2_repositories_persist_notice_document_and_rules(monkeypatch, tmp_path):
    database_path = tmp_path / "phase2.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    create_all_tables()

    with session_scope() as session:
        notice_repo = ScholarshipNoticeRepository(session)
        notice = notice_repo.upsert_notice(
            ScholarshipNoticeUpsert(
                source_board="jbnu-main",
                source_notice_id="2026-001",
                title="2026 1학기 성적우수장학금",
                notice_url="https://example.com/notices/2026-001",
                published_at=datetime(2026, 3, 1, 9, 0, tzinfo=ASIA_SEOUL),
                application_started_at=datetime(2026, 3, 2, 9, 0, tzinfo=ASIA_SEOUL),
                application_ended_at=datetime(2026, 3, 8, 18, 0, tzinfo=ASIA_SEOUL),
                summary="성적 우수 학생 대상 장학금",
            )
        )
        attachment = notice_repo.add_or_update_attachment(
            notice_id=notice.id,
            payload=NoticeAttachmentUpsert(
                source_url="https://example.com/files/2026-001.pdf",
                file_name="2026-001.pdf",
                media_type="application/pdf",
                raw_storage_path="data/raw/2026-001.pdf",
            ),
        )

        document_repo = CanonicalDocumentRepository(session)
        document = document_repo.upsert_document(
            CanonicalDocumentUpsert(
                notice_id=notice.id,
                attachment_id=attachment.id,
                document_kind=DocumentKind.ATTACHMENT_PDF,
                source_label="attachment:2026-001.pdf",
                canonical_text="직전 학기 평점 평균 3.5 이상인 재학생",
                blocks=[
                    CanonicalBlock(
                        block_id="block-1",
                        block_type="paragraph",
                        text="직전 학기 평점 평균 3.5 이상인 재학생",
                        page_number=1,
                    )
                ],
                metadata={"page_count": 1},
            )
        )
        document_repo.replace_anchors(
            document_id=document.id,
            anchors=[
                ProvenanceAnchorCreate(
                    document_id=document.id,
                    anchor_key="eligibility-gpa",
                    block_id="block-1",
                    quote_text="직전 학기 평점 평균 3.5 이상인 재학생",
                    page_number=1,
                    locator={"section": "지원자격"},
                )
            ],
        )

        rule_repo = ScholarshipRuleRepository(session)
        rule_repo.replace_rules(
            notice_id=notice.id,
            rules=[
                ScholarshipRuleCreate(
                    notice_id=notice.id,
                    document_id=document.id,
                    scholarship_name="성적우수장학금",
                    application_started_at=datetime(2026, 3, 2, 9, 0, tzinfo=ASIA_SEOUL),
                    application_ended_at=datetime(2026, 3, 8, 18, 0, tzinfo=ASIA_SEOUL),
                    summary_text="직전 학기 성적 기준 장학금",
                    qualification={
                        "gpa_min": 3.5,
                        "enrollment_status": ["재학생"],
                    },
                    provenance_keys=["eligibility-gpa"],
                )
            ],
        )

    with session_scope() as session:
        notice_repo = ScholarshipNoticeRepository(session)
        stored_notice = notice_repo.get_by_source_identity("jbnu-main", "2026-001")
        assert stored_notice is not None
        assert stored_notice.title == "2026 1학기 성적우수장학금"
        assert len(stored_notice.attachments) == 1

        document_repo = CanonicalDocumentRepository(session)
        stored_document = document_repo.get_document(
            notice_id=stored_notice.id,
            attachment_id=stored_notice.attachments[0].id,
            document_kind=DocumentKind.ATTACHMENT_PDF,
        )
        assert stored_document is not None
        assert stored_document.blocks_json[0]["text"] == "직전 학기 평점 평균 3.5 이상인 재학생"
        assert document_repo.list_anchors(stored_document.id)[0].anchor_key == "eligibility-gpa"

        rule_repo = ScholarshipRuleRepository(session)
        stored_rules = rule_repo.list_rules_for_notice(stored_notice.id)
        assert len(stored_rules) == 1
        assert stored_rules[0].qualification_json["gpa_min"] == 3.5
        assert stored_rules[0].provenance_keys_json == ["eligibility-gpa"]
