from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from app.collectors.sources import JBNU_SOFTWARE_NOTICE_SOURCE
from app.core.time import ASIA_SEOUL
from app.db import create_all_tables, session_scope
from app.models import DocumentKind, RuleStatus
from app.normalizers import AttachmentDocumentNormalizer, HwpPreviewTextExtractor
from app.repositories import CanonicalDocumentRepository, ScholarshipNoticeRepository, ScholarshipRuleRepository
from app.schemas import (
    CanonicalBlock,
    CanonicalDocumentUpsert,
    ProvenanceAnchorCreate,
    ScholarshipNoticeUpsert,
    ScholarshipRuleCreate,
)
from app.services import (
    AttachmentNormalizationService,
    NoticeCollectionService,
    NoticeHtmlNormalizationService,
    ScholarshipRuleExtractionService,
)
from app.storage import LocalRawStorage

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "collector"
REFERENCE_TIME = datetime(2026, 3, 22, 12, 0, tzinfo=ASIA_SEOUL)


def _load_fixture(name: str) -> str:
    """Read one collector HTML fixture from disk."""

    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _build_simple_pdf_bytes(text: str) -> bytes:
    """Build a minimal single-page PDF that contains one text line."""

    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_text = "BT\n/F1 12 Tf\n72 720 Td\n({0}) Tj\nET".format(escaped_text)
    stream_bytes = stream_text.encode("utf-8")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf_parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for index, object_body in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in pdf_parts))
        pdf_parts.append(
            "{0} 0 obj\n".format(index).encode("ascii") + object_body + b"\nendobj\n"
        )

    xref_offset = sum(len(part) for part in pdf_parts)
    xref_entries = [b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref_entries.append("{0:010d} 00000 n \n".format(offset).encode("ascii"))

    pdf_parts.extend(
        [
            b"xref\n0 6\n",
            b"".join(xref_entries),
            b"trailer\n<< /Size 6 /Root 1 0 R >>\n",
            b"startxref\n",
            str(xref_offset).encode("ascii") + b"\n",
            b"%%EOF\n",
        ]
    )
    return b"".join(pdf_parts)


class FakeScholarshipHwpExtractor(HwpPreviewTextExtractor):
    """Deterministic HWP preview text used to drive rule extraction tests."""

    def extract(self, raw_bytes: bytes) -> str:
        return "\n".join(
            [
                "직전학기 평점평균 3.20 이상인 재학생",
                "소득분위 8분위 이하 학생",
                "제출서류: 장학금지원서, 성적증명서, 통장사본",
            ]
        )


def seed_phase6_search_data(monkeypatch, tmp_path) -> Dict[str, int]:
    """Build one open rule and one closed rule for phase 6 search tests."""

    database_path = tmp_path / "phase6.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    create_all_tables()

    storage = LocalRawStorage(base_path=str(tmp_path / "raw"))
    fixture_map = {
        "https://software.jbnu.ac.kr/software/3348/subview.do": _load_fixture("software_notice_list.html"),
        "https://software.jbnu.ac.kr/bbs/software/527/384006/artclView.do": _load_fixture(
            "software_notice_detail.html"
        ),
    }
    binary_map = {
        "https://software.jbnu.ac.kr/uploads/song-eun-application.hwp": b"fake-hwp-binary",
        "https://software.jbnu.ac.kr/uploads/song-eun-guide.pdf": _build_simple_pdf_bytes("Song eun guide"),
    }

    NoticeCollectionService(
        fetch_html=fixture_map.__getitem__,
        fetch_binary=binary_map.__getitem__,
        raw_storage=storage,
    ).collect_source(JBNU_SOFTWARE_NOTICE_SOURCE, limit=10)

    with session_scope() as session:
        notice_repository = ScholarshipNoticeRepository(session)
        notice = notice_repository.get_by_source_identity("jbnu-software", "384006")
        assert notice is not None
        hwp_attachment = next(
            attachment for attachment in notice.attachments if attachment.file_name.endswith(".hwp")
        )
        open_notice_id = notice.id
        open_attachment_id = hwp_attachment.id

    NoticeHtmlNormalizationService(raw_storage=storage).normalize_notice(open_notice_id)
    AttachmentNormalizationService(
        raw_storage=storage,
        normalizer=AttachmentDocumentNormalizer(hwp_extractor=FakeScholarshipHwpExtractor()),
    ).normalize_attachment(open_attachment_id)
    ScholarshipRuleExtractionService().extract_notice(open_notice_id)

    with session_scope() as session:
        notice_repository = ScholarshipNoticeRepository(session)
        rule_repository = ScholarshipRuleRepository(session)
        document_repository = CanonicalDocumentRepository(session)

        open_notice = notice_repository.get_by_id(open_notice_id)
        assert open_notice is not None
        open_notice.application_started_at = REFERENCE_TIME - timedelta(days=2)
        open_notice.application_ended_at = REFERENCE_TIME + timedelta(days=5)
        open_rule = rule_repository.list_rules_for_notice(open_notice_id)[0]
        open_rule.application_started_at = open_notice.application_started_at
        open_rule.application_ended_at = open_notice.application_ended_at

        closed_notice = notice_repository.upsert_notice(
            ScholarshipNoticeUpsert(
                source_board="jbnu-main",
                source_notice_id="closed-001",
                title="2026학년도 국가근로장학금 마감 안내",
                notice_url="https://www.jbnu.ac.kr/kor/?menuID=139&pno=1&mode=view&no=999999",
                published_at=REFERENCE_TIME - timedelta(days=10),
                department_name="학생지원과",
                application_started_at=REFERENCE_TIME - timedelta(days=9),
                application_ended_at=REFERENCE_TIME - timedelta(days=1),
                summary="국가근로장학금 신청 기간이 종료된 공지",
                raw_html_path=None,
            )
        )
        closed_document = document_repository.upsert_document(
            CanonicalDocumentUpsert(
                notice_id=closed_notice.id,
                attachment_id=None,
                document_kind=DocumentKind.NOTICE_HTML,
                source_label="manual-closed-notice",
                canonical_text=(
                    "국가근로장학금 신청은 종료되었습니다.\n"
                    "재학생 대상이며 제출서류는 근로신청서입니다."
                ),
                blocks=[
                    CanonicalBlock(
                        block_id="block-1",
                        text="국가근로장학금 신청은 종료되었습니다.",
                    ),
                    CanonicalBlock(
                        block_id="block-2",
                        text="재학생 대상이며 제출서류는 근로신청서입니다.",
                    ),
                ],
                metadata={"seeded": True},
            )
        )
        document_repository.replace_anchors(
            closed_document.id,
            [
                ProvenanceAnchorCreate(
                    document_id=closed_document.id,
                    anchor_key="closed_deadline",
                    block_id="block-1",
                    quote_text="국가근로장학금 신청은 종료되었습니다.",
                    locator={"block_id": "block-1"},
                ),
                ProvenanceAnchorCreate(
                    document_id=closed_document.id,
                    anchor_key="closed_enrollment",
                    block_id="block-2",
                    quote_text="재학생 대상이며 제출서류는 근로신청서입니다.",
                    locator={"block_id": "block-2"},
                ),
            ],
        )
        rule_repository.replace_rules(
            closed_notice.id,
            [
                ScholarshipRuleCreate(
                    notice_id=closed_notice.id,
                    document_id=closed_document.id,
                    scholarship_name="국가근로장학금",
                    application_started_at=closed_notice.application_started_at,
                    application_ended_at=closed_notice.application_ended_at,
                    summary_text="재학생 대상 국가근로장학금 모집",
                    qualification={
                        "enrollment_status": ["재학생"],
                        "required_documents": ["근로신청서"],
                    },
                    provenance_keys=["closed_deadline", "closed_enrollment"],
                    status=RuleStatus.PUBLISHED,
                )
            ],
        )

        open_rule_id = open_rule.id
        closed_rule_id = rule_repository.list_rules_for_notice(closed_notice.id)[0].id

    return {
        "open_notice_id": open_notice_id,
        "open_attachment_id": open_attachment_id,
        "open_rule_id": open_rule_id,
        "closed_rule_id": closed_rule_id,
    }
