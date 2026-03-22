from io import BytesIO

from app.models import DocumentKind
from app.normalizers import AttachmentDocumentNormalizer, HwpPreviewTextExtractor


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


def test_phase4_attachment_normalizer_extracts_pdf_text():
    normalizer = AttachmentDocumentNormalizer()

    payload = normalizer.normalize_attachment(
        notice_id=1,
        attachment_id=10,
        file_name="guide.pdf",
        media_type="application/pdf",
        raw_bytes=_build_simple_pdf_bytes("PDF scholarship guide"),
    )

    assert payload.document_kind == DocumentKind.ATTACHMENT_PDF
    assert "PDF scholarship guide" in payload.canonical_text
    assert payload.blocks[0].metadata["file_name"] == "guide.pdf"


def test_phase4_hwp_preview_extractor_reads_prv_text(monkeypatch):
    class FakePreviewStream:
        def read(self):
            return "한글 장학 안내".encode("utf-16le")

    class FakeOleFile:
        def __init__(self, _stream):
            self.stream = BytesIO()

        def exists(self, name):
            return name == "PrvText"

        def openstream(self, name):
            assert name == "PrvText"
            return FakePreviewStream()

        def close(self):
            return None

    monkeypatch.setattr("app.normalizers.attachments.olefile.OleFileIO", FakeOleFile)

    extractor = HwpPreviewTextExtractor()
    extracted = extractor.extract(b"fake-hwp-binary")

    assert extracted == "한글 장학 안내"
