"""Repositories package."""

from app.repositories.document_repository import CanonicalDocumentRepository
from app.repositories.notice_repository import ScholarshipNoticeRepository
from app.repositories.rule_repository import ScholarshipRuleRepository

__all__ = [
    "CanonicalDocumentRepository",
    "ScholarshipNoticeRepository",
    "ScholarshipRuleRepository",
]
