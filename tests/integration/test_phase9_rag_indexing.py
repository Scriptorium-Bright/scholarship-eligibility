from datetime import datetime

from app.ai.providers import FakeEmbeddingProvider
from app.core.time import ASIA_SEOUL
from app.db import create_all_tables, session_scope
from app.models import DocumentKind
from app.repositories import (
    CanonicalDocumentRepository,
    ScholarshipNoticeRepository,
    ScholarshipRagChunkRepository,
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
from app.services import ScholarshipRagIndexingService


def _seed_notice_for_phase9_indexing():
    with session_scope() as session:
        notice_repository = ScholarshipNoticeRepository(session)
        document_repository = CanonicalDocumentRepository(session)
        rule_repository = ScholarshipRuleRepository(session)

        notice = notice_repository.upsert_notice(
            ScholarshipNoticeUpsert(
                source_board="jbnu-main",
                source_notice_id="2026-010",
                title="2026학년도 1학기 통합장학금 선발 안내",
                notice_url="https://example.test/notices/2026-010",
                published_at=datetime(2026, 4, 3, 9, 0, tzinfo=ASIA_SEOUL),
                application_started_at=datetime(2026, 4, 4, 9, 0, tzinfo=ASIA_SEOUL),
                application_ended_at=datetime(2026, 4, 10, 18, 0, tzinfo=ASIA_SEOUL),
                summary="평점과 소득분위를 함께 보는 장학금",
            )
        )
        attachment = notice_repository.add_or_update_attachment(
            notice.id,
            NoticeAttachmentUpsert(
                source_url="https://example.test/notices/2026-010/guide.txt",
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
                        "통합장학금",
                        "직전학기 평점평균 3.20 이상",
                        "소득분위 8분위 이하 학생",
                    ]
                ),
                blocks=[
                    CanonicalBlock(
                        block_id="notice-block-1",
                        text="통합장학금",
                        page_number=1,
                    ),
                    CanonicalBlock(
                        block_id="notice-block-2",
                        text="직전학기 평점평균 3.20 이상",
                        page_number=1,
                        metadata={"section": "지원자격"},
                    ),
                    CanonicalBlock(
                        block_id="notice-block-3",
                        text="소득분위 8분위 이하 학생",
                        page_number=1,
                        metadata={"section": "지원자격"},
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
                canonical_text="제출서류: 장학금지원서",
                blocks=[
                    CanonicalBlock(
                        block_id="attachment-block-1",
                        text="제출서류: 장학금지원서",
                        page_number=2,
                        metadata={"section": "제출서류"},
                    )
                ],
            )
        )

        document_repository.replace_anchors(
            document_id=notice_document.id,
            anchors=[
                ProvenanceAnchorCreate(
                    document_id=notice_document.id,
                    anchor_key="eligibility-gpa",
                    block_id="notice-block-2",
                    quote_text="직전학기 평점평균 3.20 이상",
                    page_number=1,
                    locator={"section": "지원자격"},
                ),
                ProvenanceAnchorCreate(
                    document_id=notice_document.id,
                    anchor_key="eligibility-income",
                    block_id="notice-block-3",
                    quote_text="소득분위 8분위 이하 학생",
                    page_number=1,
                    locator={"section": "지원자격"},
                ),
            ],
        )
        document_repository.replace_anchors(
            document_id=attachment_document.id,
            anchors=[
                ProvenanceAnchorCreate(
                    document_id=attachment_document.id,
                    anchor_key="required-documents",
                    block_id="attachment-block-1",
                    quote_text="제출서류: 장학금지원서",
                    page_number=2,
                    locator={"section": "제출서류"},
                )
            ],
        )

        saved_rules = rule_repository.replace_rules(
            notice_id=notice.id,
            rules=[
                ScholarshipRuleCreate(
                    notice_id=notice.id,
                    document_id=notice_document.id,
                    scholarship_name="통합장학금",
                    application_started_at=datetime(2026, 4, 4, 9, 0, tzinfo=ASIA_SEOUL),
                    application_ended_at=datetime(2026, 4, 10, 18, 0, tzinfo=ASIA_SEOUL),
                    summary_text="평점과 소득분위를 함께 보는 장학금",
                    qualification={
                        "gpa_min": 3.2,
                        "income_bracket_max": 8,
                        "required_documents": ["장학금지원서"],
                    },
                    provenance_keys=[
                        "eligibility-gpa",
                        "eligibility-income",
                        "required-documents",
                    ],
                )
            ],
        )

        return notice.id, saved_rules[0].id


def test_phase9_rag_indexing_service_materializes_canonical_blocks(monkeypatch, tmp_path):
    database_path = tmp_path / "phase9_indexing.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    monkeypatch.setenv("JBNU_EMBEDDING_PROVIDER", "fake")
    create_all_tables()

    notice_id, rule_id = _seed_notice_for_phase9_indexing()
    provider = FakeEmbeddingProvider()
    service = ScholarshipRagIndexingService(embedding_provider=provider)

    saved_chunks = service.rebuild_notice(notice_id)

    assert len(saved_chunks) == 4
    assert provider.recorded_document_batches
    assert any(chunk.rule_id == rule_id for chunk in saved_chunks)
    assert any(chunk.anchor_keys_json == ["eligibility-gpa"] for chunk in saved_chunks)
    assert any(chunk.anchor_keys_json == ["required-documents"] for chunk in saved_chunks)
    assert all(chunk.embedding_vector_json for chunk in saved_chunks)

    with session_scope() as session:
        rag_repository = ScholarshipRagChunkRepository(session)
        stored_chunks = rag_repository.list_chunks_for_notice(notice_id)

        assert len(stored_chunks) == 4
        assert any("통합장학금" in chunk.search_text for chunk in stored_chunks)
        assert any(chunk.metadata_json["notice_title"] == "2026학년도 1학기 통합장학금 선발 안내" for chunk in stored_chunks)


def test_phase9_rag_indexing_service_rebuilds_all_published_notices(monkeypatch, tmp_path):
    database_path = tmp_path / "phase9_indexing_all.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    monkeypatch.setenv("JBNU_EMBEDDING_PROVIDER", "fake")
    create_all_tables()

    notice_id, _ = _seed_notice_for_phase9_indexing()
    provider = FakeEmbeddingProvider()
    service = ScholarshipRagIndexingService(embedding_provider=provider)

    rebuilt_chunks = service.rebuild_published_notices()

    assert len(rebuilt_chunks) == 4

    with session_scope() as session:
        rag_repository = ScholarshipRagChunkRepository(session)
        assert len(rag_repository.list_chunks_for_notice(notice_id)) == 4
