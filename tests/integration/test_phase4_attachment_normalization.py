from pathlib import Path

from app.collectors.sources import JBNU_MAIN_NOTICE_SOURCE, JBNU_SOFTWARE_NOTICE_SOURCE
from app.db import create_all_tables, session_scope
from app.models import DocumentKind
from app.normalizers import AttachmentDocumentNormalizer, HwpPreviewTextExtractor
from app.repositories import CanonicalDocumentRepository, ScholarshipNoticeRepository
from app.services import AttachmentNormalizationService, NoticeCollectionService
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


class FakeHwpPreviewExtractor(HwpPreviewTextExtractor):
    """Deterministic extractor used to test HWP normalization service wiring."""

    def extract(self, raw_bytes: bytes) -> str:
        return "송은장학금 지원서 미리보기"


def test_phase4_attachment_normalization_service_persists_pdf_and_hwp_documents(monkeypatch, tmp_path):
    database_path = tmp_path / "phase4_attachment.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    create_all_tables()

    storage = LocalRawStorage(base_path=str(tmp_path / "raw"))
    fixture_map = {
        "https://www.jbnu.ac.kr/web/news/notice/sub01.do": _load_fixture("jbnu_main_notice_list.html"),
        "https://www.jbnu.ac.kr/web/news/notice/sub01.do?mode=view&articleNo=402100": _load_fixture(
            "jbnu_main_notice_detail.html"
        ),
        "https://software.jbnu.ac.kr/software/3348/subview.do": _load_fixture("software_notice_list.html"),
        "https://software.jbnu.ac.kr/bbs/software/527/384006/artclView.do": _load_fixture(
            "software_notice_detail.html"
        ),
    }
    binary_map = {
        "https://www.jbnu.ac.kr/files/work-study-guide.pdf": _build_simple_pdf_bytes("Work study guide"),
        "https://software.jbnu.ac.kr/uploads/song-eun-application.hwp": b"fake-hwp-binary",
        "https://software.jbnu.ac.kr/uploads/song-eun-guide.pdf": _build_simple_pdf_bytes("Song eun guide"),
    }

    collection_service = NoticeCollectionService(
        fetch_html=fixture_map.__getitem__,
        fetch_binary=binary_map.__getitem__,
        raw_storage=storage,
    )
    collection_service.collect_source(JBNU_MAIN_NOTICE_SOURCE, limit=10)
    collection_service.collect_source(JBNU_SOFTWARE_NOTICE_SOURCE, limit=10)

    with session_scope() as session:
        notice_repository = ScholarshipNoticeRepository(session)
        main_notice = notice_repository.get_by_source_identity("jbnu-main", "402100")
        software_notice = notice_repository.get_by_source_identity("jbnu-software", "384006")
        assert main_notice is not None
        assert software_notice is not None

        main_pdf_attachment = main_notice.attachments[0]
        hwp_attachment = next(
            attachment for attachment in software_notice.attachments if attachment.file_name.endswith(".hwp")
        )

    service = AttachmentNormalizationService(raw_storage=storage)
    pdf_document = service.normalize_attachment(main_pdf_attachment.id)

    hwp_service = AttachmentNormalizationService(
        raw_storage=storage,
        normalizer=AttachmentDocumentNormalizer(hwp_extractor=FakeHwpPreviewExtractor()),
    )
    hwp_document = hwp_service.normalize_attachment(hwp_attachment.id)

    with session_scope() as session:
        repository = CanonicalDocumentRepository(session)
        stored_pdf = repository.get_document(
            notice_id=pdf_document.notice_id,
            attachment_id=pdf_document.attachment_id,
            document_kind=DocumentKind.ATTACHMENT_PDF,
        )
        stored_hwp = repository.get_document(
            notice_id=hwp_document.notice_id,
            attachment_id=hwp_document.attachment_id,
            document_kind=DocumentKind.ATTACHMENT_TEXT,
        )

        assert stored_pdf is not None
        assert "Work study guide" in stored_pdf.canonical_text
        assert stored_hwp is not None
        assert "송은장학금 지원서 미리보기" in stored_hwp.canonical_text
