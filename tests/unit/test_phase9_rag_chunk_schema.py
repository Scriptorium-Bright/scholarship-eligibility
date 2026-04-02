from app.models import ScholarshipRagChunk
from app.models.base import Base
from app.models.common import DocumentKind
from app.schemas import ScholarshipRagChunkUpsert


def test_phase9_rag_chunk_table_is_registered_in_metadata():
    table_names = set(Base.metadata.tables.keys())

    assert "scholarship_rag_chunks" in table_names


def test_phase9_rag_chunk_has_chunk_key_constraint():
    constraints = {
        constraint.name
        for constraint in ScholarshipRagChunk.__table__.constraints
        if constraint.name
    }

    assert "uq_scholarship_rag_chunk_key" in constraints


def test_phase9_rag_chunk_upsert_schema_keeps_anchor_keys_and_embedding():
    payload = ScholarshipRagChunkUpsert(
        notice_id=1,
        document_id=2,
        rule_id=3,
        chunk_key="notice-1:block-1",
        block_id="block-1",
        chunk_text="직전 학기 평점 평균 3.5 이상",
        search_text="성적우수장학금 직전 학기 평점 평균 3.5 이상",
        scholarship_name="성적우수장학금",
        source_label="attachment:guide.pdf",
        document_kind=DocumentKind.ATTACHMENT_PDF,
        page_number=1,
        anchor_keys=["eligibility-gpa"],
        embedding_vector=[1.0, 0.0, 0.0],
        metadata={"section": "지원자격"},
    )

    assert payload.document_kind == DocumentKind.ATTACHMENT_PDF
    assert payload.anchor_keys == ["eligibility-gpa"]
    assert payload.embedding_vector == [1.0, 0.0, 0.0]
    assert payload.metadata["section"] == "지원자격"
