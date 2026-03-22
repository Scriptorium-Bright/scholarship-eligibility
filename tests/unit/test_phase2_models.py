from datetime import datetime

from app.core.time import ASIA_SEOUL
from app.models import ScholarshipNotice
from app.models.base import Base
from app.schemas import CanonicalBlock, ScholarshipNoticeUpsert


def test_phase2_tables_are_registered_in_metadata():
    table_names = set(Base.metadata.tables.keys())

    assert "scholarship_notices" in table_names
    assert "notice_attachments" in table_names
    assert "canonical_documents" in table_names
    assert "provenance_anchors" in table_names
    assert "scholarship_rules" in table_names


def test_scholarship_notice_has_source_identity_constraint():
    constraints = {
        constraint.name
        for constraint in ScholarshipNotice.__table__.constraints
        if constraint.name
    }

    assert "uq_scholarship_notice_source_identity" in constraints


def test_notice_schema_validates_expected_payload():
    payload = ScholarshipNoticeUpsert(
        source_board="jbnu-main",
        source_notice_id="2026-001",
        title="2026 1학기 성적우수장학금",
        notice_url="https://example.com/notices/2026-001",
        published_at=datetime(2026, 3, 1, 9, 0, tzinfo=ASIA_SEOUL),
        summary="성적 기준 장학금 공지",
    )

    assert payload.source_board == "jbnu-main"
    assert payload.source_notice_id == "2026-001"


def test_canonical_block_schema_keeps_metadata():
    block = CanonicalBlock(
        block_id="block-1",
        text="직전 학기 평점 평균 3.5 이상",
        page_number=2,
        metadata={"section": "지원자격"},
    )

    assert block.page_number == 2
    assert block.metadata["section"] == "지원자격"
