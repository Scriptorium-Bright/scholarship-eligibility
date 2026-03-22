from __future__ import annotations

from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import RuleStatus, ScholarshipRule
from app.schemas import ScholarshipRuleCreate


class ScholarshipRuleRepository:
    """Persist and query structured scholarship rules."""

    def __init__(self, session: Session):
        self.session = session

    def replace_rules(
        self,
        notice_id: int,
        rules: List[ScholarshipRuleCreate],
    ) -> List[ScholarshipRule]:
        """Replace all extracted rules for a notice with the latest version."""

        self.session.execute(
            delete(ScholarshipRule).where(ScholarshipRule.notice_id == notice_id)
        )

        saved_rules = []
        for payload in rules:
            payload_data = payload.model_dump()
            payload_data["qualification_json"] = payload_data.pop("qualification")
            payload_data["provenance_keys_json"] = payload_data.pop("provenance_keys")
            rule = ScholarshipRule(**payload_data)
            self.session.add(rule)
            saved_rules.append(rule)

        self.session.flush()
        return saved_rules

    def list_rules_for_notice(self, notice_id: int) -> List[ScholarshipRule]:
        """Return all rules extracted from a single notice."""

        statement = (
            select(ScholarshipRule)
            .where(ScholarshipRule.notice_id == notice_id)
            .order_by(ScholarshipRule.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_published_rules(self, limit: Optional[int] = None) -> List[ScholarshipRule]:
        """Return published rules for future search and eligibility APIs."""

        statement = (
            select(ScholarshipRule)
            .where(ScholarshipRule.status == RuleStatus.PUBLISHED)
            .order_by(ScholarshipRule.id.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.scalars(statement))
