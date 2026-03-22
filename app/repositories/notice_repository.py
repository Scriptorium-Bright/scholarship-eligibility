from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import NoticeAttachment, ScholarshipNotice
from app.schemas import NoticeAttachmentUpsert, ScholarshipNoticeUpsert


class ScholarshipNoticeRepository:
    """Persist and query collected notice metadata."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_source_identity(
        self,
        source_board: str,
        source_notice_id: str,
    ) -> Optional[ScholarshipNotice]:
        """Fetch a notice by the external board identity used during collection."""

        statement = (
            select(ScholarshipNotice)
            .where(ScholarshipNotice.source_board == source_board)
            .where(ScholarshipNotice.source_notice_id == source_notice_id)
            .options(selectinload(ScholarshipNotice.attachments))
        )
        return self.session.scalar(statement)

    def get_by_id(self, notice_id: int) -> Optional[ScholarshipNotice]:
        """Fetch one notice by internal database id."""

        statement = (
            select(ScholarshipNotice)
            .where(ScholarshipNotice.id == notice_id)
            .options(selectinload(ScholarshipNotice.attachments))
        )
        return self.session.scalar(statement)

    def upsert_notice(self, payload: ScholarshipNoticeUpsert) -> ScholarshipNotice:
        """Insert a new notice or refresh an existing one with latest metadata."""

        notice = self.get_by_source_identity(payload.source_board, payload.source_notice_id)
        payload_data = payload.model_dump()

        if notice is None:
            notice = ScholarshipNotice(**payload_data)
            self.session.add(notice)
        else:
            for field_name, value in payload_data.items():
                setattr(notice, field_name, value)

        self.session.flush()
        return notice

    def add_or_update_attachment(
        self,
        notice_id: int,
        payload: NoticeAttachmentUpsert,
    ) -> NoticeAttachment:
        """Insert or refresh an attachment for a previously collected notice."""

        statement = (
            select(NoticeAttachment)
            .where(NoticeAttachment.notice_id == notice_id)
            .where(NoticeAttachment.source_url == payload.source_url)
        )
        attachment = self.session.scalar(statement)
        payload_data = payload.model_dump()

        if attachment is None:
            attachment = NoticeAttachment(notice_id=notice_id, **payload_data)
            self.session.add(attachment)
        else:
            for field_name, value in payload_data.items():
                setattr(attachment, field_name, value)

        self.session.flush()
        return attachment

    def list_recent_notices(self, limit: int = 20) -> List[ScholarshipNotice]:
        """Return recently published notices for later collector checks or APIs."""

        statement = (
            select(ScholarshipNotice)
            .order_by(ScholarshipNotice.published_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
