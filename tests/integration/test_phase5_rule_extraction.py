from pathlib import Path

from app.collectors.sources import JBNU_SOFTWARE_NOTICE_SOURCE
from app.db import create_all_tables, session_scope
from app.normalizers import AttachmentDocumentNormalizer, HwpPreviewTextExtractor
from app.repositories import CanonicalDocumentRepository, ScholarshipNoticeRepository, ScholarshipRuleRepository
from app.services import (
    AttachmentNormalizationService,
    NoticeCollectionService,
    NoticeHtmlNormalizationService,
    ScholarshipRuleExtractionService,
)
from app.storage import LocalRawStorage

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "collector"


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


def test_phase5_rule_extraction_service_persists_rule_and_provenance(monkeypatch, tmp_path):
    database_path = tmp_path / "phase5.sqlite3"
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

    collection_service = NoticeCollectionService(
        fetch_html=fixture_map.__getitem__,
        fetch_binary=binary_map.__getitem__,
        raw_storage=storage,
    )
    collection_service.collect_source(JBNU_SOFTWARE_NOTICE_SOURCE, limit=10)

    with session_scope() as session:
        notice_repository = ScholarshipNoticeRepository(session)
        notice = notice_repository.get_by_source_identity("jbnu-software", "384006")
        assert notice is not None
        hwp_attachment = next(
            attachment for attachment in notice.attachments if attachment.file_name.endswith(".hwp")
        )
        notice_id = notice.id

    NoticeHtmlNormalizationService(raw_storage=storage).normalize_notice(notice_id)
    AttachmentNormalizationService(
        raw_storage=storage,
        normalizer=AttachmentDocumentNormalizer(hwp_extractor=FakeScholarshipHwpExtractor()),
    ).normalize_attachment(hwp_attachment.id)

    saved_rules = ScholarshipRuleExtractionService().extract_notice(notice_id)
    assert len(saved_rules) == 1

    with session_scope() as session:
        rule_repository = ScholarshipRuleRepository(session)
        document_repository = CanonicalDocumentRepository(session)
        notice_rules = rule_repository.list_rules_for_notice(notice_id)
        attachment_document = next(
            document
            for document in document_repository.list_documents_for_notice(notice_id)
            if document.attachment_id == hwp_attachment.id
        )
        anchors = document_repository.list_anchors(attachment_document.id)

        assert notice_rules[0].scholarship_name == "송은장학금"
        assert notice_rules[0].qualification_json["gpa_min"] == 3.2
        assert notice_rules[0].qualification_json["income_bracket_max"] == 8
        assert notice_rules[0].qualification_json["enrollment_status"] == ["재학생"]
        assert "장학금지원서" in notice_rules[0].qualification_json["required_documents"]
        assert notice_rules[0].provenance_keys_json
        assert anchors
