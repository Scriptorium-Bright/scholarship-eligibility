from datetime import datetime

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
    ScholarshipRagChunkUpsert,
    ScholarshipRuleCreate,
)


def test_phase9_rag_chunk_repository_persists_and_retrieves_candidates(monkeypatch, tmp_path):
    database_path = tmp_path / "phase9.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    create_all_tables()

    with session_scope() as session:
        notice_repo = ScholarshipNoticeRepository(session)
        notice = notice_repo.upsert_notice(
            ScholarshipNoticeUpsert(
                source_board="jbnu-main",
                source_notice_id="2026-009",
                title="2026 1학기 통합장학금",
                notice_url="https://example.com/notices/2026-009",
                published_at=datetime(2026, 4, 1, 9, 0, tzinfo=ASIA_SEOUL),
                application_started_at=datetime(2026, 4, 2, 9, 0, tzinfo=ASIA_SEOUL),
                application_ended_at=datetime(2026, 4, 8, 18, 0, tzinfo=ASIA_SEOUL),
                summary="성적 및 소득 기준 통합 장학금",
            )
        )
        attachment = notice_repo.add_or_update_attachment(
            notice_id=notice.id,
            payload=NoticeAttachmentUpsert(
                source_url="https://example.com/files/2026-009.pdf",
                file_name="2026-009.pdf",
                media_type="application/pdf",
                raw_storage_path="data/raw/2026-009.pdf",
            ),
        )

        document_repo = CanonicalDocumentRepository(session)
        document = document_repo.upsert_document(
            CanonicalDocumentUpsert(
                notice_id=notice.id,
                attachment_id=attachment.id,
                document_kind=DocumentKind.ATTACHMENT_PDF,
                source_label="attachment:2026-009.pdf",
                canonical_text=(
                    "직전 학기 평점 평균 3.5 이상인 재학생\n"
                    "소득분위 8분위 이하 학생"
                ),
                blocks=[
                    CanonicalBlock(
                        block_id="block-1",
                        block_type="paragraph",
                        text="직전 학기 평점 평균 3.5 이상인 재학생",
                        page_number=1,
                    ),
                    CanonicalBlock(
                        block_id="block-2",
                        block_type="paragraph",
                        text="소득분위 8분위 이하 학생",
                        page_number=1,
                    ),
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
                ),
                ProvenanceAnchorCreate(
                    document_id=document.id,
                    anchor_key="eligibility-income",
                    block_id="block-2",
                    quote_text="소득분위 8분위 이하 학생",
                    page_number=1,
                    locator={"section": "지원자격"},
                ),
            ],
        )

        rule_repo = ScholarshipRuleRepository(session)
        saved_rules = rule_repo.replace_rules(
            notice_id=notice.id,
            rules=[
                ScholarshipRuleCreate(
                    notice_id=notice.id,
                    document_id=document.id,
                    scholarship_name="통합장학금",
                    application_started_at=datetime(2026, 4, 2, 9, 0, tzinfo=ASIA_SEOUL),
                    application_ended_at=datetime(2026, 4, 8, 18, 0, tzinfo=ASIA_SEOUL),
                    summary_text="성적 및 소득 기준 통합 장학금",
                    qualification={
                        "gpa_min": 3.5,
                        "income_bracket_max": 8,
                    },
                    provenance_keys=["eligibility-gpa", "eligibility-income"],
                )
            ],
        )

        rag_repo = ScholarshipRagChunkRepository(session)
        rag_repo.upsert_chunks(
            [
                ScholarshipRagChunkUpsert(
                    notice_id=notice.id,
                    document_id=document.id,
                    rule_id=saved_rules[0].id,
                    chunk_key="2026-009:block-1",
                    block_id="block-1",
                    chunk_text="직전 학기 평점 평균 3.5 이상인 재학생",
                    search_text="통합장학금 직전 학기 평점 평균 3.5 이상인 재학생",
                    scholarship_name="통합장학금",
                    source_label="attachment:2026-009.pdf",
                    document_kind=DocumentKind.ATTACHMENT_PDF,
                    page_number=1,
                    anchor_keys=["eligibility-gpa"],
                    embedding_vector=[1.0, 0.0, 0.0],
                    metadata={"section": "지원자격"},
                ),
                ScholarshipRagChunkUpsert(
                    notice_id=notice.id,
                    document_id=document.id,
                    rule_id=saved_rules[0].id,
                    chunk_key="2026-009:block-2",
                    block_id="block-2",
                    chunk_text="소득분위 8분위 이하 학생",
                    search_text="통합장학금 소득분위 8분위 이하 학생",
                    scholarship_name="통합장학금",
                    source_label="attachment:2026-009.pdf",
                    document_kind=DocumentKind.ATTACHMENT_PDF,
                    page_number=1,
                    anchor_keys=["eligibility-income"],
                    embedding_vector=[0.6, 0.8, 0.0],
                    metadata={"section": "지원자격"},
                ),
            ]
        )

    with session_scope() as session:
        rag_repo = ScholarshipRagChunkRepository(session)

        stored_chunks = rag_repo.list_chunks_for_notice(notice.id)
        assert len(stored_chunks) == 2
        assert stored_chunks[0].chunk_key == "2026-009:block-1"
        assert stored_chunks[1].anchor_keys_json == ["eligibility-income"]

        keyword_candidates = rag_repo.list_keyword_candidates("평점 3.5", limit=2)
        assert len(keyword_candidates) == 1
        assert keyword_candidates[0].chunk_key == "2026-009:block-1"
        assert keyword_candidates[0].retrieval_kind == "keyword"

        vector_candidates = rag_repo.list_vector_candidates([1.0, 0.0, 0.0], limit=2)
        assert len(vector_candidates) == 2
        assert vector_candidates[0].chunk_key == "2026-009:block-1"
        assert vector_candidates[0].score == 1.0
        assert vector_candidates[1].chunk_key == "2026-009:block-2"

        hydrated_chunks = rag_repo.list_chunks_by_ids([vector_candidates[0].chunk_id])
        assert len(hydrated_chunks) == 1
        assert hydrated_chunks[0].metadata_json["section"] == "지원자격"

        deleted_count = rag_repo.delete_by_notice_ids([notice.id])
        assert deleted_count == 2
        assert rag_repo.list_chunks_for_notice(notice.id) == []
