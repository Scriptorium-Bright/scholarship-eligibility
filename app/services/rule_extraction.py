from __future__ import annotations

from collections import defaultdict
from time import perf_counter
from typing import Dict, List, Optional, Tuple

from app.ai.providers import StructuredOutputProviderError, build_structured_output_provider
from app.core.config import Settings, get_settings
from app.db import session_scope
from app.extractors import (
    HeuristicScholarshipRuleExtractor,
    ExtractedScholarshipRule,
    LLMScholarshipRuleExtractor,
    NoticeExtractionPromptBuilder,
    StructuredRuleExtractor,
)
from app.repositories import CanonicalDocumentRepository, ScholarshipNoticeRepository, ScholarshipRuleRepository
from app.schemas import ProvenanceAnchorCreate, ScholarshipRuleCreate
from app.services.extraction_logging import ExtractionOutcomeLog, log_extraction_result


class ScholarshipRuleExtractionService:
    """canonical document에서 구조화된 장학 규정과 근거를 추출하는 서비스입니다."""

    def __init__(
        self,
        extractor: Optional[StructuredRuleExtractor] = None,
        settings: Optional[Settings] = None,
    ):
        """
        공용 structured extraction contract를 따르는 구현체를 주입받아 초기화합니다.
        phase 8부터는 heuristic extractor와 future LLM extractor가 같은 자리에서 교체됩니다.
        """

        self._settings = settings or get_settings()
        self._requested_mode = "custom" if extractor is not None else self._settings.extractor_mode
        if extractor is not None:
            self._extractor = extractor
            self._fallback_extractor = None
        else:
            self._extractor, self._fallback_extractor = self._build_default_extractors(self._settings)

    def extract_notice(self, notice_id: int):
        """
        해당 공지사항에 속한 정규화 문서 집합을 불러와 장학금 선발 규정과 근거(Provenance)를 체계적으로 추출합니다.
        생성된 구조화된 규칙들을 DB의 기존 룰 내역 및 앵커 데이터와 원자적으로 교체(Replace)합니다.
        """

        started_at = perf_counter()
        extractor_used = self._label_extractor(self._extractor)
        fallback_error: Optional[Exception] = None

        with session_scope() as session:
            notice_repository = ScholarshipNoticeRepository(session)
            document_repository = CanonicalDocumentRepository(session)
            rule_repository = ScholarshipRuleRepository(session)

            notice = notice_repository.get_by_id(notice_id)
            if notice is None:
                raise ValueError("Notice does not exist: {0}".format(notice_id))

            canonical_documents = document_repository.list_documents_for_notice(notice_id)
            if not canonical_documents:
                raise ValueError("Notice does not have canonical documents: {0}".format(notice_id))

            try:
                extracted_rule, extractor_used, fallback_error = self._extract_rule(
                    notice_title=notice.title,
                    canonical_documents=canonical_documents,
                    application_started_at=notice.application_started_at,
                    application_ended_at=notice.application_ended_at,
                    fallback_summary=notice.summary,
                )

                saved_rules = rule_repository.replace_rules(
                    notice_id=notice.id,
                    rules=[
                        ScholarshipRuleCreate(
                            notice_id=notice.id,
                            document_id=extracted_rule.source_document_id,
                            scholarship_name=extracted_rule.scholarship_name,
                            application_started_at=extracted_rule.application_started_at,
                            application_ended_at=extracted_rule.application_ended_at,
                            summary_text=extracted_rule.summary_text,
                            qualification=extracted_rule.qualification,
                            provenance_keys=[anchor.anchor_key for anchor in extracted_rule.provenance_anchors],
                            status=extracted_rule.status,
                        )
                    ],
                )

                anchors_by_document: Dict[int, List[ProvenanceAnchorCreate]] = defaultdict(list)
                for anchor in extracted_rule.provenance_anchors:
                    anchors_by_document[anchor.document_id].append(
                        ProvenanceAnchorCreate(
                            document_id=anchor.document_id,
                            anchor_key=anchor.anchor_key,
                            block_id=anchor.block_id,
                            quote_text=anchor.quote_text,
                            page_number=anchor.page_number,
                            locator=anchor.locator,
                        )
                    )

                for document_id, anchors in anchors_by_document.items():
                    document_repository.replace_anchors(document_id=document_id, anchors=anchors)

                self._log_extraction_outcome(
                    notice_id=notice.id,
                    extractor_used=extractor_used,
                    started_at=started_at,
                    success=True,
                    fallback_error=fallback_error,
                )
                return saved_rules
            except Exception as exc:
                self._log_extraction_outcome(
                    notice_id=notice.id,
                    extractor_used=extractor_used,
                    started_at=started_at,
                    success=False,
                    fallback_error=fallback_error,
                    raised_error=exc,
                )
                raise

    def _extract_rule(
        self,
        *,
        notice_title: str,
        canonical_documents: List[object],
        application_started_at,
        application_ended_at,
        fallback_summary: Optional[str],
    ) -> Tuple[ExtractedScholarshipRule, str, Optional[Exception]]:
        """
        요청된 추출 모드에 따라 heuristic, llm, hybrid 경로를 실행합니다.
        hybrid에서는 LLM 실패를 fallback 후보로 판정한 뒤 heuristic 결과로 복구할 수 있게 분기합니다.
        """

        if self._requested_mode == "hybrid":
            try:
                extracted_rule = self._run_extractor(
                    extractor=self._extractor,
                    notice_title=notice_title,
                    canonical_documents=canonical_documents,
                    application_started_at=application_started_at,
                    application_ended_at=application_ended_at,
                    fallback_summary=fallback_summary,
                )
                return extracted_rule, self._label_extractor(self._extractor), None
            except (StructuredOutputProviderError, ValueError) as exc:
                if self._fallback_extractor is None:
                    raise
                extracted_rule = self._run_extractor(
                    extractor=self._fallback_extractor,
                    notice_title=notice_title,
                    canonical_documents=canonical_documents,
                    application_started_at=application_started_at,
                    application_ended_at=application_ended_at,
                    fallback_summary=fallback_summary,
                )
                return extracted_rule, self._label_extractor(self._fallback_extractor), exc

        extracted_rule = self._run_extractor(
            extractor=self._extractor,
            notice_title=notice_title,
            canonical_documents=canonical_documents,
            application_started_at=application_started_at,
            application_ended_at=application_ended_at,
            fallback_summary=fallback_summary,
        )
        return extracted_rule, self._label_extractor(self._extractor), None

    def _run_extractor(
        self,
        *,
        extractor: StructuredRuleExtractor,
        notice_title: str,
        canonical_documents: List[object],
        application_started_at,
        application_ended_at,
        fallback_summary: Optional[str],
    ) -> ExtractedScholarshipRule:
        """추출 구현체 공통 contract를 호출해 단일 규정 결과를 반환합니다."""

        return extractor.extract_notice_rule(
            notice_title=notice_title,
            canonical_documents=canonical_documents,
            application_started_at=application_started_at,
            application_ended_at=application_ended_at,
            fallback_summary=fallback_summary,
        )

    def _build_default_extractors(
        self, settings: Settings
    ) -> Tuple[StructuredRuleExtractor, Optional[StructuredRuleExtractor]]:
        """애플리케이션 설정에 따라 기본 추출기와 선택적 fallback 추출기를 조립합니다."""

        if settings.extractor_mode == "heuristic":
            return HeuristicScholarshipRuleExtractor(), None
        if settings.extractor_mode == "llm":
            return self._build_llm_extractor(settings), None
        if settings.extractor_mode == "hybrid":
            return self._build_llm_extractor(settings), HeuristicScholarshipRuleExtractor()
        raise ValueError(
            "Extractor mode is not supported in phase 8.5: {0}".format(settings.extractor_mode)
        )

    def _build_llm_extractor(self, settings: Settings) -> LLMScholarshipRuleExtractor:
        """설정값을 반영한 provider와 prompt builder를 묶어 LLM extractor를 만듭니다."""

        return LLMScholarshipRuleExtractor(
            provider=build_structured_output_provider(settings),
            prompt_builder=NoticeExtractionPromptBuilder(
                max_characters=settings.llm_max_context_characters
            ),
        )

    def _label_extractor(self, extractor: StructuredRuleExtractor) -> str:
        """로그와 문서에서 읽기 쉬운 extractor 식별 문자열을 반환합니다."""

        if isinstance(extractor, LLMScholarshipRuleExtractor):
            return "llm"
        if isinstance(extractor, HeuristicScholarshipRuleExtractor):
            return "heuristic"
        return extractor.__class__.__name__

    def _log_extraction_outcome(
        self,
        *,
        notice_id: int,
        extractor_used: str,
        started_at: float,
        success: bool,
        fallback_error: Optional[Exception] = None,
        raised_error: Optional[Exception] = None,
    ) -> None:
        """phase 8.5 운영 로그 형식에 맞춰 추출 성공, fallback, 실패 결과를 남깁니다."""

        final_error = raised_error or fallback_error
        log_extraction_result(
            ExtractionOutcomeLog(
                notice_id=notice_id,
                requested_mode=self._requested_mode,
                extractor_used=extractor_used,
                success=success,
                fallback_used=fallback_error is not None,
                latency_ms=(perf_counter() - started_at) * 1000,
                error_type=type(final_error).__name__ if final_error is not None else None,
                error_message=str(final_error) if final_error is not None else None,
            )
        )
