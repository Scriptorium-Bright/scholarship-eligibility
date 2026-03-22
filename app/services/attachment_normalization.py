from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.db import session_scope
from app.models import NoticeAttachment
from app.normalizers import AttachmentDocumentNormalizer
from app.repositories import CanonicalDocumentRepository
from app.storage import LocalRawStorage


class AttachmentNormalizationService:
    """Read stored attachment binaries and persist canonical attachment documents."""

    def __init__(
        self,
        raw_storage: Optional[LocalRawStorage] = None,
        normalizer: Optional[AttachmentDocumentNormalizer] = None,
    ):
        """Prepare the raw storage adapter and attachment normalizer."""

        self._raw_storage = raw_storage or LocalRawStorage()
        self._normalizer = normalizer or AttachmentDocumentNormalizer()

    def normalize_attachment(self, attachment_id: int):
        """Normalize one stored attachment into a canonical document row."""

        with session_scope() as session:
            attachment = session.scalar(
                select(NoticeAttachment).where(NoticeAttachment.id == attachment_id)
            )
            if attachment is None:
                raise ValueError("Attachment does not exist: {0}".format(attachment_id))
            if not attachment.raw_storage_path:
                raise ValueError("Attachment does not have stored raw content: {0}".format(attachment_id))

            raw_bytes = self._raw_storage.read_bytes(attachment.raw_storage_path)
            payload = self._normalizer.normalize_attachment(
                notice_id=attachment.notice_id,
                attachment_id=attachment.id,
                file_name=attachment.file_name,
                media_type=attachment.media_type,
                raw_bytes=raw_bytes,
            )

            repository = CanonicalDocumentRepository(session)
            return repository.upsert_document(payload)
