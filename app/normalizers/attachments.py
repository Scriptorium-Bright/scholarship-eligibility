from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple

import olefile
from pypdf import PdfReader

from app.models import DocumentKind
from app.schemas import CanonicalBlock, CanonicalDocumentUpsert


class UnsupportedAttachmentError(ValueError):
    """Raised when no extractor is available for the attachment payload."""


def _clean_text(text: str) -> str:
    """Normalize repeated whitespace for extracted attachment text."""

    return " ".join((text or "").split())


class PdfAttachmentTextExtractor:
    """Extract text from PDF attachments using pypdf."""

    def extract(self, raw_bytes: bytes) -> str:
        """Return concatenated text for all pages in the PDF payload."""

        reader = PdfReader(BytesIO(raw_bytes))
        page_texts = []
        for page in reader.pages:
            extracted = _clean_text(page.extract_text() or "")
            if extracted:
                page_texts.append(extracted)
        return "\n".join(page_texts).strip()


class HwpPreviewTextExtractor:
    """Extract preview text from HWP attachments through the OLE `PrvText` stream."""

    def extract(self, raw_bytes: bytes) -> str:
        """Read the `PrvText` preview stream and decode it as UTF-16LE text."""

        ole = olefile.OleFileIO(BytesIO(raw_bytes))
        try:
            if not ole.exists("PrvText"):
                raise UnsupportedAttachmentError("HWP preview text stream is missing")
            preview_stream = ole.openstream("PrvText")
            preview_bytes = preview_stream.read()
        finally:
            ole.close()

        extracted = _clean_text(preview_bytes.decode("utf-16le", errors="ignore"))
        if not extracted:
            raise UnsupportedAttachmentError("HWP preview text is empty")
        return extracted


class PlainTextAttachmentTextExtractor:
    """Decode text-like attachment bytes as UTF-8."""

    def extract(self, raw_bytes: bytes) -> str:
        """Decode plain text bytes and normalize the resulting whitespace."""

        extracted = _clean_text(raw_bytes.decode("utf-8"))
        if not extracted:
            raise UnsupportedAttachmentError("Plain text attachment is empty")
        return extracted


class AttachmentDocumentNormalizer:
    """Convert raw attachment bytes into canonical document payloads."""

    def __init__(
        self,
        pdf_extractor: Optional[PdfAttachmentTextExtractor] = None,
        hwp_extractor: Optional[HwpPreviewTextExtractor] = None,
        text_extractor: Optional[PlainTextAttachmentTextExtractor] = None,
    ):
        """Prepare extractor implementations used for different attachment types."""

        self._pdf_extractor = pdf_extractor or PdfAttachmentTextExtractor()
        self._hwp_extractor = hwp_extractor or HwpPreviewTextExtractor()
        self._text_extractor = text_extractor or PlainTextAttachmentTextExtractor()

    def normalize_attachment(
        self,
        notice_id: int,
        attachment_id: int,
        file_name: str,
        media_type: str,
        raw_bytes: bytes,
    ) -> CanonicalDocumentUpsert:
        """Extract text from one attachment and wrap it as a canonical document."""

        document_kind, extracted_text = self._extract_text(file_name, media_type, raw_bytes)
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        block_texts = lines or [extracted_text]
        blocks = [
            CanonicalBlock(
                block_id="block-{0}".format(index + 1),
                block_type="attachment_text",
                text=block_text,
                metadata={"file_name": file_name},
            )
            for index, block_text in enumerate(block_texts)
        ]

        return CanonicalDocumentUpsert(
            notice_id=notice_id,
            attachment_id=attachment_id,
            document_kind=document_kind,
            source_label="attachment:{0}".format(file_name),
            canonical_text="\n".join(block.text for block in blocks),
            blocks=blocks,
            metadata={
                "file_name": file_name,
                "media_type": media_type,
                "attachment_id": attachment_id,
            },
        )

    def _extract_text(
        self,
        file_name: str,
        media_type: str,
        raw_bytes: bytes,
    ) -> Tuple[DocumentKind, str]:
        """Pick the extractor that matches the attachment extension or media type."""

        extension = Path(file_name).suffix.lower()
        if extension == ".pdf" or media_type == "application/pdf":
            extracted = self._pdf_extractor.extract(raw_bytes)
            if not extracted:
                raise UnsupportedAttachmentError("PDF attachment does not contain extractable text")
            return DocumentKind.ATTACHMENT_PDF, extracted

        if extension == ".hwp" or media_type == "application/x-hwp":
            return DocumentKind.ATTACHMENT_TEXT, self._hwp_extractor.extract(raw_bytes)

        if media_type.startswith("text/") or extension in {".txt", ".md"}:
            return DocumentKind.ATTACHMENT_TEXT, self._text_extractor.extract(raw_bytes)

        raise UnsupportedAttachmentError(
            "Unsupported attachment type: {0} ({1})".format(file_name, media_type)
        )
